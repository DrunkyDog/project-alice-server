-- liquibase formatted sql

-- changeset DrunkyDog:202607312200
-- Register the MiniMax global (api.minimax.io) TTS provider so it can be configured
-- from the console like every other model. Unlike the built-in minimax_httpstream it
-- needs no group_id, and it returns a full MP3 that the base class converts to Opus.

DELETE FROM `ai_model_provider` WHERE id = 'SYSTEM_TTS_MinimaxIOTTS';
INSERT INTO `ai_model_provider`
    (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
VALUES
    ('SYSTEM_TTS_MinimaxIOTTS', 'TTS', 'minimax_io', 'MiniMax Global TTS (api.minimax.io)',
     '[{"key":"api_key","label":"API key","type":"string"},
       {"key":"voice_id","label":"Voice id (cloned voices moss_audio_... work here)","type":"string"},
       {"key":"model","label":"Model","type":"string"},
       {"key":"language_boost","label":"Language boost (Thai fixes pronunciation)","type":"string"},
       {"key":"emotion","label":"Emotion: happy / sad / angry / fearful / disgusted / surprised / calm","type":"string"},
       {"key":"speed","label":"Speed [0.5-2]","type":"string"},
       {"key":"vol","label":"Volume (0-10]","type":"string"},
       {"key":"pitch","label":"Pitch [-12-12]","type":"string"},
       {"key":"sample_rate","label":"Sample rate","type":"string"},
       {"key":"format","label":"Audio format: mp3 / pcm / flac","type":"string"},
       {"key":"laugh_555","label":"Speak Thai 555 as laughter: true / false","type":"string"},
       {"key":"sound_effects","label":"Sound effect, e.g. spacious_echo (optional)","type":"string"},
       {"key":"host","label":"API host","type":"string"},
       {"key":"output_dir","label":"Output directory","type":"string"}]',
     19, 1, NOW(), 1, NOW());

DELETE FROM `ai_model_config` WHERE id = 'TTS_MinimaxIOTTS';
INSERT INTO `ai_model_config`
    (`id`, `model_type`, `model_code`, `model_name`, `is_default`, `is_enabled`, `config_json`,
     `doc_link`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`)
VALUES
    ('TTS_MinimaxIOTTS', 'TTS', 'MinimaxIOTTS', 'MiniMax Global TTS', 0, 1,
     '{"type": "minimax_io", "api_key": "", "voice_id": "", "model": "speech-2.8-hd", "language_boost": "Thai", "emotion": "happy", "speed": "1.0", "vol": "1.0", "pitch": "0", "sample_rate": "32000", "format": "mp3", "laugh_555": "true", "sound_effects": "", "host": "api.minimax.io", "output_dir": "tmp/"}',
     'https://www.minimax.io/platform',
     'MiniMax T2A v2 on the global endpoint. Notes:
1. Get an API key from https://www.minimax.io/platform — the global host needs no group_id.
2. language_boost = Thai is what makes Thai pronunciation correct; change it for other languages.
3. voice_id accepts system voices and cloned voices (moss_audio_...). A voice picked on the agent overrides it.
4. laugh_555 rewrites Thai chat-laughter "555" into laughter tags instead of reading it as a number. It needs a speech-2.8 model (2.8-hd / 2.8-turbo); set it to false on older models.
5. Non-streaming: it returns a full MP3 that the server converts to Opus, which plays reliably on the device. Use the streaming provider only if latency matters more than reliability.',
     22, 1, NOW(), 1, NOW());

-- Reuse the voice list already seeded for the streaming MiniMax model: same platform,
-- same system voice ids. Cloned voices are entered directly in voice_id instead.
DELETE FROM `ai_tts_voice` WHERE tts_model_id = 'TTS_MinimaxIOTTS';
INSERT INTO `ai_tts_voice`
    (`id`, `tts_model_id`, `name`, `tts_voice`, `languages`, `voice_demo`, `remark`, `sort`,
     `creator`, `create_date`, `updater`, `update_date`)
SELECT REPLACE(`id`, 'TTS_MinimaxStreamTTS', 'TTS_MinimaxIOTTS'),
       'TTS_MinimaxIOTTS', `name`, `tts_voice`, `languages`, `voice_demo`, `remark`, `sort`,
       1, NOW(), 1, NOW()
FROM `ai_tts_voice`
WHERE tts_model_id = 'TTS_MinimaxStreamTTS';
