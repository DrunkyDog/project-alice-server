import json
import time
import uuid
import hmac
import base64
import hashlib
import asyncio
import requests
import websockets
from urllib import parse
from datetime import datetime
from config.logger import setup_logging
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


class AccessToken:
    @staticmethod
    def _encode_text(text):
        encoded_text = parse.quote_plus(text)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def _encode_dict(dic):
        keys = dic.keys()
        dic_sorted = [(key, dic[key]) for key in sorted(keys)]
        encoded_text = parse.urlencode(dic_sorted)
        return encoded_text.replace("+", "%20").replace("*", "%2A").replace("%7E", "~")

    @staticmethod
    def create_token(access_key_id, access_key_secret):
        parameters = {
            "AccessKeyId": access_key_id,
            "Action": "CreateToken",
            "Format": "JSON",
            "RegionId": "cn-shanghai",
            "SignatureMethod": "HMAC-SHA1",
            "SignatureNonce": str(uuid.uuid1()),
            "SignatureVersion": "1.0",
            "Timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "Version": "2019-02-28",
        }
        query_string = AccessToken._encode_dict(parameters)
        string_to_sign = (
            "GET" + "&" + AccessToken._encode_text("/") + "&" + AccessToken._encode_text(query_string)
        )
        secreted_string = hmac.new(
            bytes(access_key_secret + "&", encoding="utf-8"),
            bytes(string_to_sign, encoding="utf-8"),
            hashlib.sha1,
        ).digest()
        signature = base64.b64encode(secreted_string)
        signature = AccessToken._encode_text(signature)
        full_url = "http://nls-meta.cn-shanghai.aliyuncs.com/?Signature=%s&%s" % (signature, query_string)
        response = requests.get(full_url)
        if response.ok:
            root_obj = response.json()
            if "Token" in root_obj:
                return root_obj["Token"]["Id"], root_obj["Token"]["ExpireTime"]
        return None, None


class ASRProvider(ASRProviderBase):
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.text = ""
        self.asr_ws = None
        self.forward_task = None
        self.is_processing = False
        self.server_ready = False  # Server ready state

        # Basic configuration
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.appkey = config.get("appkey")
        self.token = config.get("token")
        self.host = config.get("host", "nls-gateway-cn-shanghai.aliyuncs.com")
        # If the host is an internal address (containing -internal.aliyuncs.com), use the ws protocol; otherwise, use wss by default.
        if "-internal." in self.host:
            self.ws_url = f"ws://{self.host}/ws/v1"
        else:
            # Use wss by default.
            self.ws_url = f"wss://{self.host}/ws/v1"

        self.max_sentence_silence = config.get("max_sentence_silence")
        self.output_dir = config.get("output_dir", "./audio_output")
        self.delete_audio_file = delete_audio_file
        self.expire_time = None

        self.task_id = uuid.uuid4().hex

        # Token management
        if self.access_key_id and self.access_key_secret:
            self._refresh_token()
        elif not self.token:
            raise ValueError("You must provide access_key_id and access_key_secret, or provide a token directly")

    def _refresh_token(self):
        """Refresh the token."""
        self.token, expire_time_str = AccessToken.create_token(self.access_key_id, self.access_key_secret)
        if not self.token:
            raise ValueError("Unable to obtain a valid access token")
        
        try:
            expire_str = str(expire_time_str).strip()
            if expire_str.isdigit():
                expire_time = datetime.fromtimestamp(int(expire_str))
            else:
                expire_time = datetime.strptime(expire_str, "%Y-%m-%dT%H:%M:%SZ")
            self.expire_time = expire_time.timestamp() - 60
        except:
            self.expire_time = None

    def _is_token_expired(self):
        """Check whether the token has expired."""
        return self.expire_time and time.time() > self.expire_time

    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)

    async def receive_audio(self, conn, pcm_frame, audio_have_voice):
        # First call the parent method to handle the base logic.
        await super().receive_audio(conn, pcm_frame, audio_have_voice)

        # Only establish a connection when there is audio and no connection exists (excluding the stopping state).
        if audio_have_voice and not self.is_processing and not self.asr_ws:
            try:
                await self._start_recognition(conn)
            except Exception as e:
                logger.bind(tag=TAG).error(f"Recognition start failed: {str(e)}")
                await self._cleanup()
                return

        if self.asr_ws and self.is_processing and self.server_ready:
            try:
                await self.asr_ws.send(pcm_frame)
            except Exception as e:
                logger.bind(tag=TAG).warning(f"Failed to send audio: {str(e)}")
                await self._cleanup()

    async def _start_recognition(self, conn: "ConnectionHandler"):
        """Start the recognition session."""
        if self._is_token_expired():
            self._refresh_token()
        
        # Establish the connection.
        headers = {"X-NLS-Token": self.token}
        self.asr_ws = await websockets.connect(
            self.ws_url,
            additional_headers=headers,
            max_size=1000000000,
            ping_interval=None,
            ping_timeout=None,
            close_timeout=5,
        )

        self.task_id = uuid.uuid4().hex

        logger.bind(tag=TAG).debug(f"WebSocket connection established successfully, task_id: {self.task_id}")

        self.is_processing = True
        self.server_ready = False  # Reset the server-ready state
        self.forward_task = asyncio.create_task(self._forward_results(conn))

        # Send the start request.
        start_request = {
            "header": {
                "namespace": "SpeechTranscriber",
                "name": "StartTranscription",
                "message_id": uuid.uuid4().hex,
                "task_id": self.task_id,
                "appkey": self.appkey
            },
            "payload": {
                "format": "pcm",
                "sample_rate": 16000,
                "enable_intermediate_result": True,
                "enable_punctuation_prediction": True,
                "enable_inverse_text_normalization": True,
                "max_sentence_silence": self.max_sentence_silence,
                "enable_voice_detection": False,
            }
        }
        await self.asr_ws.send(json.dumps(start_request, ensure_ascii=False))
        logger.bind(tag=TAG).debug("Start request sent; waiting for the server to be ready...")

    async def _forward_results(self, conn: "ConnectionHandler"):
        """Forward recognition results."""
        try:
            while not conn.stop_event.is_set():
                # Get the audio data for the current connection.
                audio_data = conn.asr_audio
                try:
                    response = await self.asr_ws.recv()
                    result = json.loads(response)

                    header = result.get("header", {})
                    payload = result.get("payload", {})
                    message_name = header.get("name", "")
                    status = header.get("status", 0)

                    if status != 20000000:
                        if status == 40010004:
                            logger.bind(tag=TAG).warning(f"Please wait for the server response to finish before closing the connection; status code: {status}")
                            break
                        if status in [40000004, 40010003]:  # Connection timed out or the client disconnected
                            logger.bind(tag=TAG).warning(f"Connection issue; status code: {status}")
                            break
                        elif status in [40270002, 40270003]:  # Audio-related issue
                            logger.bind(tag=TAG).warning(f"Audio processing issue; status code: {status}")
                            continue
                        else:
                            logger.bind(tag=TAG).error(f"Recognition error; status code: {status}, message: {header.get('status_text', '')}")
                            continue

                    # Receiving TranscriptionStarted means the server is ready to receive audio data.
                    if message_name == "TranscriptionStarted":
                        self.server_ready = True
                        logger.bind(tag=TAG).debug("The server is ready; sending cached audio...")

                        # Send cached audio.
                        if conn.asr_audio:
                            for cached_pcm in conn.asr_audio[-10:]:
                                try:
                                    await self.asr_ws.send(cached_pcm)
                                except Exception as e:
                                    logger.bind(tag=TAG).warning(f"Failed to send cached audio: {e}")
                                    break
                        continue
                    elif message_name == "SentenceEnd":
                        # Sentence end (triggered for each sentence).
                        text = payload.get("result", "")
                        if text:
                            logger.bind(tag=TAG).info(f"Recognized text: {text}")

                            # In manual mode, accumulate the recognition results.
                            if conn.client_listen_mode == "manual":
                                if self.text:
                                    self.text += text
                                else:
                                    self.text = text

                                # In manual mode, processing is triggered only after the stop signal is received (once only).
                                if conn.client_voice_stop:
                                    logger.bind(tag=TAG).debug("Received the final recognition result; triggering processing")
                                    await self.handle_voice_stop(conn, audio_data)
                                    break
                            else:
                                # In automatic mode, overwrite directly.
                                self.text = text
                                await self.handle_voice_stop(conn, audio_data)
                                break

                except asyncio.TimeoutError:
                    logger.bind(tag=TAG).error("Receiving results timed out")
                    break
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).info("The ASR service connection has been closed")
                    self.is_processing = False
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"Failed to process results: {str(e)}")
                    break

        except Exception as e:
            logger.bind(tag=TAG).error(f"Result forwarding failed: {str(e)}")
        finally:
            # Clean up the connected audio cache.
            await self._cleanup()
            conn.reset_audio_states()

    async def _send_stop_request(self):
        """Send a stop-recognition request without closing the connection."""
        if self.asr_ws:
            try:
                # Stop sending audio first.
                self.is_processing = False

                stop_msg = {
                    "header": {
                        "namespace": "SpeechTranscriber",
                        "name": "StopTranscription",
                        "message_id": uuid.uuid4().hex,
                        "task_id": self.task_id,
                        "appkey": self.appkey
                    }
                }
                logger.bind(tag=TAG).debug("Stop-recognition request sent")
                await self.asr_ws.send(json.dumps(stop_msg, ensure_ascii=False))
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to send the stop-recognition request: {e}")

    async def _cleanup(self):
        """Clean up resources and close the connection."""
        logger.bind(tag=TAG).debug(f"Starting ASR session cleanup | current state: processing={self.is_processing}, server_ready={self.server_ready}")

        # Reset the state.
        self.is_processing = False
        self.server_ready = False
        logger.bind(tag=TAG).debug("ASR state reset")

        # Close the connection.
        if self.asr_ws:
            try:
                logger.bind(tag=TAG).debug("Closing the WebSocket connection")
                await asyncio.wait_for(self.asr_ws.close(), timeout=2.0)
                logger.bind(tag=TAG).debug("WebSocket connection closed")
            except Exception as e:
                logger.bind(tag=TAG).error(f"Failed to close the WebSocket connection: {e}")
            finally:
                self.asr_ws = None

        # Clear the task references.
        self.forward_task = None

        logger.bind(tag=TAG).debug("ASR session cleanup complete")

    async def speech_to_text(self, opus_data, session_id, artifacts=None):
        """Get the recognition result."""
        result = self.text
        self.text = ""
        return result, None

    async def close(self):
        """Close resources."""
        await self._cleanup()
