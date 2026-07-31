import os
import json
import time
import base64
import asyncio
from typing import Optional, Tuple, List

from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType
from core.providers.asr.base import ASRProviderBase

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleAuthRequest

TAG = __name__
logger = setup_logging()

STT_ENDPOINT = "https://speech.googleapis.com/v1/speech:recognize"
SCOPE = "https://www.googleapis.com/auth/cloud-platform"


class ASRProvider(ASRProviderBase):
    """
    Google Cloud Speech-to-Text (v1 REST, service-account auth).

    NON_STREAM / requires_file: the base class hands us a mono 16kHz LINEAR16 WAV
    (artifacts.file_path); we base64 it into a synchronous speech:recognize call.

    Why v1 (not Chirp v2): v1 supports speechContexts phrase-hints + per-phrase
    boost, which is the whole reason for adding this provider — nudging Thai
    proper nouns that Whisper mishears (e.g. the cat "เขียบ", "Alice").

    config keys:
      credentials_path : mounted service-account JSON (reuses the TTS one)
      language_code    : BCP-47, default "th-TH"
      model            : "latest_long" (default) | "latest_short" | "default"
      phrase_hints     : list[str] of proper nouns / jargon to bias toward
      phrase_boost     : 0-20, strength of the bias (default 15)
      enable_punctuation : bool, default true
      use_enhanced     : bool, default false (Thai has no enhanced model; leaving
                         it on can 400 for some languages)
      timeout          : seconds, default 10
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        self.interface_type = InterfaceType.NON_STREAM

        self.credentials_path = (
            config.get("credentials_path")
            or config.get("credentials_file")
            or "/opt/xiaozhi-esp32-server/data/google-tts-sa.json"
        )
        if not self.credentials_path or not os.path.exists(self.credentials_path):
            raise Exception(
                f"Google STT: service-account file not found: {self.credentials_path}"
            )
        self._credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=[SCOPE]
        )

        self.language_code = config.get("language_code") or "th-TH"
        self.model = config.get("model") or "latest_long"

        hints = config.get("phrase_hints") or []
        if isinstance(hints, str):
            # allow a comma/newline separated string from the manager UI
            hints = [h.strip() for h in hints.replace("\n", ",").split(",") if h.strip()]
        self.phrase_hints: List[str] = hints
        self.phrase_boost = float(config.get("phrase_boost", 15) or 15)

        self.enable_punctuation = bool(config.get("enable_punctuation", True))
        self.use_enhanced = bool(config.get("use_enhanced", False))
        self.timeout = int(config.get("timeout", 10) or 10)

        self.output_dir = config.get("output_dir") or "tmp/"
        self.delete_audio_file = delete_audio_file
        os.makedirs(self.output_dir, exist_ok=True)

    def requires_file(self) -> bool:
        return True

    def _get_token(self) -> str:
        # google-auth caches and only hits the network when the token expired
        if not self._credentials.valid:
            self._credentials.refresh(GoogleAuthRequest())
        return self._credentials.token

    def _recognize_blocking(self, wav_bytes: bytes) -> str:
        recognition_config = {
            "encoding": "LINEAR16",
            "sampleRateHertz": 16000,
            "audioChannelCount": 1,
            "languageCode": self.language_code,
            "model": self.model,
            "enableAutomaticPunctuation": self.enable_punctuation,
        }
        if self.use_enhanced:
            recognition_config["useEnhanced"] = True
        if self.phrase_hints:
            recognition_config["speechContexts"] = [
                {"phrases": self.phrase_hints, "boost": self.phrase_boost}
            ]

        payload = {
            "config": recognition_config,
            "audio": {"content": base64.b64encode(wav_bytes).decode("utf-8")},
        }
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json; charset=utf-8",
        }
        resp = requests.post(
            STT_ENDPOINT,
            headers=headers,
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise Exception(
                f"Google STT request failed: {resp.status_code}, {resp.text[:300]}"
            )
        # results is a list of segments; concatenate the top alternative of each
        results = resp.json().get("results", [])
        parts = [
            r["alternatives"][0]["transcript"]
            for r in results
            if r.get("alternatives") and r["alternatives"][0].get("transcript")
        ]
        return "".join(parts).strip()

    async def speech_to_text(
        self,
        opus_data: List[bytes],
        session_id: str,
        audio_format="opus",
        artifacts=None,
    ) -> Tuple[Optional[str], Optional[str]]:
        file_path = None
        try:
            if artifacts is None:
                return "", None
            file_path = artifacts.file_path
            with open(file_path, "rb") as f:
                wav_bytes = f.read()

            start_time = time.time()
            text = await asyncio.to_thread(self._recognize_blocking, wav_bytes)
            logger.bind(tag=TAG).debug(
                f"Google STT {time.time() - start_time:.3f}s | text: {text}"
            )
            return text, file_path
        except Exception as e:
            logger.bind(tag=TAG).error(f"Google STT failed: {e}")
            return "", None
