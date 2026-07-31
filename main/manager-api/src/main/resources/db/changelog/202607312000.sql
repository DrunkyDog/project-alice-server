-- liquibase formatted sql

-- changeset DrunkyDog:202607312000
-- Translate the remaining plugin names and field labels to English.
-- The function dialog renders ai_model_provider.name and fields[].label straight from the DB
-- (no i18n), so these strings stayed Chinese while the rest of the UI was English.
--
-- Labels are swapped with JSON_SET instead of rebuilding the field list, so existing keys,
-- types and defaults are preserved. Each statement is guarded by the key at that index,
-- so it turns into a no-op if the field order ever differs.

UPDATE `ai_model_provider` SET name = 'Server Music Player' WHERE id = 'SYSTEM_PLUGIN_MUSIC';
UPDATE `ai_model_provider` SET name = 'Device-to-Device Call' WHERE id = 'SYSTEM_PLUGIN_CALL_DEVICE';
UPDATE `ai_model_provider` SET name = 'Home Assistant: Set Device State' WHERE id = 'SYSTEM_PLUGIN_HA_SET_STATE';
UPDATE `ai_model_provider` SET name = 'Home Assistant: Play Music' WHERE id = 'SYSTEM_PLUGIN_HA_PLAY_MUSIC';

-- NewsNow aggregator: source names in the default value are API data, not UI text, so they stay
UPDATE `ai_model_provider` SET name = 'NewsNow Aggregator' WHERE id = 'SYSTEM_PLUGIN_NEWS_NEWSNOW';

UPDATE `ai_model_provider`
SET fields = JSON_SET(fields, '$[0].label', 'API endpoint')
WHERE id = 'SYSTEM_PLUGIN_NEWS_NEWSNOW'
  AND JSON_UNQUOTE(JSON_EXTRACT(fields, '$[0].key')) = 'url';

UPDATE `ai_model_provider`
SET fields = JSON_SET(fields, '$[1].label', 'News sources (semicolon separated)')
WHERE id = 'SYSTEM_PLUGIN_NEWS_NEWSNOW'
  AND JSON_UNQUOTE(JSON_EXTRACT(fields, '$[1].key')) = 'news_sources';

-- Home Assistant: get device state
UPDATE `ai_model_provider` SET name = 'Home Assistant: Get Device State' WHERE id = 'SYSTEM_PLUGIN_HA_GET_STATE';

UPDATE `ai_model_provider`
SET fields = JSON_SET(fields, '$[0].label', 'Home Assistant base URL')
WHERE id = 'SYSTEM_PLUGIN_HA_GET_STATE'
  AND JSON_UNQUOTE(JSON_EXTRACT(fields, '$[0].key')) = 'base_url';

UPDATE `ai_model_provider`
SET fields = JSON_SET(fields, '$[1].label', 'Home Assistant API token')
WHERE id = 'SYSTEM_PLUGIN_HA_GET_STATE'
  AND JSON_UNQUOTE(JSON_EXTRACT(fields, '$[1].key')) = 'api_key';

UPDATE `ai_model_provider`
SET fields = JSON_SET(fields, '$[2].label', 'Device list (name,entity_id; one per line)')
WHERE id = 'SYSTEM_PLUGIN_HA_GET_STATE'
  AND JSON_UNQUOTE(JSON_EXTRACT(fields, '$[2].key')) = 'devices';
