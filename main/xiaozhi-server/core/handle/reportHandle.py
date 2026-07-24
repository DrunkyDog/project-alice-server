"""
The TTS reporting feature has been integrated into the ConnectionHandler class.

The reporting features include:
1. Each connection object has its own reporting queue and processing thread.
2. The reporting thread lifecycle is bound to the connection object.
3. Reporting is performed using the ConnectionHandler.enqueue_tts_report method.

Please refer to the relevant code in core/connection.py for the concrete implementation.
"""

import time
import json
import opuslib_next
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

from config.manage_api_client import report as manage_report

TAG = __name__


async def report(conn: "ConnectionHandler", type, text, opus_data, report_time):
    """Execute chat history reporting.

    Args:
        conn: Connection object
        type: Report type, 1 for user, 2 for agent, 3 for tool call
        text: Synthesized text
        opus_data: Opus audio data
        report_time: Report time
    """
    try:
        if opus_data:
            audio_data = opus_to_wav(conn, opus_data)
        else:
            audio_data = None
        # Execute asynchronous reporting
        await manage_report(
            mac_address=conn.device_id,
            session_id=conn.session_id,
            chat_type=type,
            content=text,
            audio=audio_data,
            report_time=report_time,
        )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Chat history reporting failed: {e}")


def opus_to_wav(conn: "ConnectionHandler", pcm_data):
    """Convert PCM data to WAV-format byte streams.

    Args:
        output_dir: Output directory (reserved parameter to maintain interface compatibility)
        pcm_data: PCM audio data (may be a list or bytes)

    Returns:
        bytes: WAV-format audio data
    """
    try:
        # Handle PCM data that may be a list or bytes
        if isinstance(pcm_data, list):
            pcm_data_bytes = b"".join(pcm_data)
        else:
            pcm_data_bytes = pcm_data

        if not pcm_data_bytes:
            raise ValueError("No valid PCM data")

        # Create the WAV file header
        num_samples = len(pcm_data_bytes) // 2  # 16-bit samples

        # WAV file header
        wav_header = bytearray()
        wav_header.extend(b"RIFF")  # ChunkID
        wav_header.extend((36 + len(pcm_data_bytes)).to_bytes(4, "little"))  # ChunkSize
        wav_header.extend(b"WAVE")  # Format
        wav_header.extend(b"fmt ")  # Subchunk1ID
        wav_header.extend((16).to_bytes(4, "little"))  # Subchunk1Size
        wav_header.extend((1).to_bytes(2, "little"))  # AudioFormat (PCM)
        wav_header.extend((1).to_bytes(2, "little"))  # NumChannels
        wav_header.extend((16000).to_bytes(4, "little"))  # SampleRate
        wav_header.extend((32000).to_bytes(4, "little"))  # ByteRate
        wav_header.extend((2).to_bytes(2, "little"))  # BlockAlign
        wav_header.extend((16).to_bytes(2, "little"))  # BitsPerSample
        wav_header.extend(b"data")  # Subchunk2ID
        wav_header.extend(len(pcm_data_bytes).to_bytes(4, "little"))  # Subchunk2Size

        # Return the complete WAV data
        return bytes(wav_header) + pcm_data_bytes
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"PCM to WAV conversion failed: {e}", exc_info=True)
        raise


def enqueue_tts_report(conn: "ConnectionHandler", text, opus_data):
    if not conn.read_config_from_api or conn.need_bind or not conn.report_tts_enable:
        return
    if conn.chat_history_conf == 0:
        return
    """Add TTS data to the reporting queue.

    Args:
        conn: Connection object
        text: Synthesized text
        opus_data: Opus audio data
    """
    try:
        # Use the connection object's queue and pass the text and binary data rather than a file path
        if conn.chat_history_conf == 2:
            conn.report_queue.put((2, text, opus_data, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"TTS data added to reporting queue: {conn.device_id}, audio size: {len(opus_data)} "
            )
        else:
            conn.report_queue.put((2, text, None, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"TTS data added to reporting queue: {conn.device_id}, audio not reported"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to add TTS data to reporting queue: {text}, {e}")


def enqueue_tool_report(conn: "ConnectionHandler", tool_name: str, tool_input: dict, tool_result: str = None, report_tool_call: bool = True):
    """Add tool call data to the reporting queue.

    Args:
        conn: Connection object
        tool_name: Tool name
        tool_input: Tool input parameters
        tool_result: Tool execution result (optional)
        report_tool_call: Whether to report the tool call itself; defaults to True; set to False when only reporting the result
    """
    if not conn.read_config_from_api or conn.need_bind:
        return
    if conn.chat_history_conf == 0:
        return

    try:
        timestamp = int(time.time() * 1000)

        # Build the tool call content
        if report_tool_call:
            tool_text = json.dumps(
                [
                    {
                        "type": "tool",
                        "text": f"{tool_name}({json.dumps(tool_input, ensure_ascii=False)})",
                    }
                ]
            )
            conn.report_queue.put((3, tool_text, None, timestamp))

        # Build the tool result content
        if tool_result:
            result_display = f'{{"result":"{str(tool_result)}"}}'
            result_content = json.dumps([{"type": "tool_result", "text": result_display}], ensure_ascii=False)
            conn.report_queue.put((3, result_content, None, timestamp + 1))
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"Failed to add tool reporting data to the queue: {e}")


def enqueue_asr_report(conn: "ConnectionHandler", text, opus_data):
    if not conn.read_config_from_api or conn.need_bind or not conn.report_asr_enable:
        return
    if conn.chat_history_conf == 0:
        return
    """Add ASR data to the reporting queue.

    Args:
        conn: Connection object
        text: Synthesized text
        opus_data: Opus audio data
    """
    try:
        # Use the connection object's queue and pass the text and binary data rather than a file path
        if conn.chat_history_conf == 2:
            conn.report_queue.put((1, text, opus_data, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"ASR data added to reporting queue: {conn.device_id}, audio size: {len(opus_data)} "
            )
        else:
            conn.report_queue.put((1, text, None, int(time.time() * 1000)))
            conn.logger.bind(tag=TAG).debug(
                f"ASR data added to reporting queue: {conn.device_id}, audio not reported"
            )
    except Exception as e:
        conn.logger.bind(tag=TAG).debug(f"Failed to add ASR data to reporting queue: {text}, {e}")
