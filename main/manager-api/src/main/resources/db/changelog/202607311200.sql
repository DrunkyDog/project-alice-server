-- liquibase formatted sql

-- changeset DrunkyDog:202607311200
-- Weather plugin now falls back OpenWeatherMap -> WeatherAPI.com -> Open-Meteo; QWeather (api_host) is gone
-- Defaults are literals on purpose: 202505292203 ends with
--   DELETE FROM sys_params WHERE param_code LIKE 'plugins.%'
-- so reading them back out of sys_params would write NULL defaults into the field list.

UPDATE `ai_model_provider`
SET name = 'Weather',
    fields = JSON_ARRAY(
        JSON_OBJECT(
                'key', 'owm_api_key',
                'type', 'string',
                'label', 'OpenWeatherMap API key',
                'default', ''
        ),
        JSON_OBJECT(
                'key', 'api_key',
                'type', 'string',
                'label', 'WeatherAPI.com API key',
                'default', ''
        ),
        JSON_OBJECT(
                'key', 'default_location',
                'type', 'string',
                'label', 'Default city',
                'default', 'Bangkok'
        )
    )
WHERE id = 'SYSTEM_PLUGIN_WEATHER';

-- Agents that already had this plugin: the old api_key was a QWeather key, which the new
-- code would read as a WeatherAPI.com key. Clear it and drop the now-unused api_host.
UPDATE `ai_agent_plugin_mapping`
SET param_info = JSON_REMOVE(JSON_SET(param_info, '$.api_key', ''), '$.api_host')
WHERE plugin_id = 'SYSTEM_PLUGIN_WEATHER'
  AND JSON_EXTRACT(param_info, '$.api_host') IS NOT NULL;

-- Only migrate the city when it is still the untouched upstream default, so a city the
-- user picked on purpose is left alone
UPDATE `ai_agent_plugin_mapping`
SET param_info = JSON_SET(param_info, '$.default_location', 'Bangkok')
WHERE plugin_id = 'SYSTEM_PLUGIN_WEATHER'
  AND JSON_UNQUOTE(JSON_EXTRACT(param_info, '$.default_location')) IN ('广州', 'Guangzhou');
