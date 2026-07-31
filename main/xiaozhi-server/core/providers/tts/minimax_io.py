import os
import re
import json
import uuid
import asyncio
from datetime import datetime

import requests

from config.logger import setup_logging
from core.providers.tts.base import TTSProviderBase

TAG = __name__
logger = setup_logging()

# Standalone run of 5s (Thai chat-laughter). Negative look-around keeps phone
# numbers / prices (5550, 12555) out — only a bare "555", "5555", ... matches.
_LAUGH_555 = re.compile(r"(?<!\d)5{3,}(?!\d)")


class TTSProvider(TTSProviderBase):
    """
    MiniMax T2A v2 — GLOBAL endpoint (api.minimax.io), NON_STREAM.

    Unlike the built-in `minimax_httpstream` (mainland api.minimaxi.com + GroupId +
    server-side PCM->Opus, which failed to play on the device), this talks to the
    global .io endpoint, requests a full MP3 (stream=false), writes it to a file, and
    lets the base class convert it to Opus — the same reliable path as Edge/Google.

    config keys:
      api_key        : MiniMax global API key (required)
      voice_id       : voice id, incl. cloned voices (moss_audio_...). private_voice wins.
      model          : default "speech-2.8-hd"
      language_boost : default "Thai"  (critical for correct Thai pronunciation)
      emotion        : default "happy"
      speed / vol / pitch : voice_setting tuning
      sample_rate    : MP3 sample rate requested from MiniMax, default 32000
      format         : "mp3" (default) or "pcm"/"flac"
      sound_effects  : optional, e.g. "spacious_echo"
      host           : default "api.minimax.io"
      laugh_555      : default true. Rewrites Thai chat-laughter "555" into MiniMax
                       interjection tags so the voice laughs instead of reading
                       "ha-ha-hundred-fifty-five". 3-4 fives -> (chuckle); 5+ -> (laughs).
                       Needs a speech-2.8 model (2.8-hd/2.8-turbo support these tags).

    Tuning keys are read flat first, then from the nested voice_setting/audio_setting
    dicts, so a config copied from the built-in minimax provider still works.
    """

    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)

        self.api_key = config.get("api_key")
        if not self.api_key:
            raise Exception("MiniMax(.io) TTS: api_key is required")

        voice_setting = config.get("voice_setting") or {}
        audio_setting = config.get("audio_setting") or {}

        def pick(key, section, default):
            # The console saves untouched fields as "", so treat empty as unset
            for source in (config, section):
                value = source.get(key)
                if value not in (None, ""):
                    return value
            return default

        self.voice_id = (
            config.get("private_voice")
            or config.get("voice_id")
            or config.get("voice")
            or voice_setting.get("voice_id")
        )
        self.model = config.get("model") or "speech-2.8-hd"
        self.language_boost = config.get("language_boost") or "Thai"
        self.emotion = pick("emotion", voice_setting, "happy")

        self.speed = float(pick("speed", voice_setting, 1))
        self.vol = float(pick("vol", voice_setting, 1))
        self.pitch = int(pick("pitch", voice_setting, 0))

        self.sample_rate = int(pick("sample_rate", audio_setting, 32000))
        self.audio_file_type = str(pick("format", audio_setting, "mp3")).lower()
        self.sound_effects = config.get("sound_effects")  # e.g. "spacious_echo"

        laugh = config.get("laugh_555", True)
        self.laugh_555 = str(laugh).lower() not in ("false", "0", "no", "off", "")

        self.host = config.get("host") or "api.minimax.io"
        self.api_url = f"https://{self.host}/v1/t2a_v2"

        logger.bind(tag=TAG).info(
            f"MiniMax(.io) TTS ready | model={self.model} | voice={self.voice_id} "
            f"| language_boost={self.language_boost} | format={self.audio_file_type}"
        )

    def generate_filename(self, extension=None):
        ext = extension or f".{self.audio_file_type}"
        return os.path.join(
            self.output_file,
            f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{ext}",
        )

    def _preprocess_text(self, text):
        # Turn "555" chat-laughter into interjection tags: soft (chuckle) for a
        # short burst, loud (laughs) for a long one. Length is judged per match.
        if not self.laugh_555 or not text:
            return text

        def _repl(m):
            return " (laughs) " if len(m.group(0)) >= 5 else " (chuckle) "

        return _LAUGH_555.sub(_repl, text)

    def _synthesize_blocking(self, text):
        text = self._preprocess_text(text)
        voice_setting = {
            "voice_id": self.voice_id,
            "speed": self.speed,
            "vol": self.vol,
            "pitch": self.pitch,
            "emotion": self.emotion,
        }
        payload = {
            "model": self.model,
            "text": text,
            "stream": False,
            "voice_setting": voice_setting,
            "audio_setting": {
                "sample_rate": self.sample_rate,
                "format": self.audio_file_type,
                "channel": 1,
            },
            "language_boost": self.language_boost,
            "output_format": "hex",
        }
        if self.sound_effects:
            payload["voice_modify"] = {
                "pitch": 0,
                "intensity": 0,
                "timbre": 0,
                "sound_effects": self.sound_effects,
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        resp = requests.post(
            self.api_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=self.tts_timeout,
        )
        if resp.status_code != 200:
            raise Exception(
                f"MiniMax TTS request failed: {resp.status_code}, {resp.text[:300]}"
            )
        data = resp.json()

        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code", 0) != 0:
            raise Exception(
                f"MiniMax TTS error {base_resp.get('status_code')}: "
                f"{base_resp.get('status_msg')}"
            )

        audio_hex = (data.get("data") or {}).get("audio")
        if not audio_hex:
            raise Exception("MiniMax TTS returned empty audio")
        return bytes.fromhex(audio_hex)

    async def text_to_speak(self, text, output_file):
        audio_bytes = await asyncio.to_thread(self._synthesize_blocking, text)
        if output_file:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "wb") as f:
                f.write(audio_bytes)
        else:
            return audio_bytes
