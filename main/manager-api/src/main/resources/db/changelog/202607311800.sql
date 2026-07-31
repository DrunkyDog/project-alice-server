-- liquibase formatted sql

-- changeset DrunkyDog:202607311800
-- Web search goes Thai-first: sources are Tavily -> Brave, Metaso is dropped,
-- plus new language / country / length settings

UPDATE `ai_model_provider`
SET name = 'Web Search',
    fields = JSON_ARRAY(
        JSON_OBJECT(
                'key', 'provider',
                'type', 'string',
                'label', 'Search source: auto / tavily / brave',
                'default', 'auto'
        ),
        JSON_OBJECT(
                'key', 'api_key',
                'type', 'string',
                'label', 'Tavily API key (starts with tvly-)',
                'default', ''
        ),
        JSON_OBJECT(
                'key', 'brave_api_key',
                'type', 'string',
                'label', 'Brave Search API key',
                'default', ''
        ),
        JSON_OBJECT(
                'key', 'max_results',
                'type', 'string',
                'label', 'Number of results',
                'default', '5'
        ),
        JSON_OBJECT(
                'key', 'country',
                'type', 'string',
                'label', 'Result country (ISO 2 letters, e.g. TH)',
                'default', 'TH'
        ),
        JSON_OBJECT(
                'key', 'lang',
                'type', 'string',
                'label', 'Result language (e.g. th)',
                'default', 'th'
        ),
        JSON_OBJECT(
                'key', 'max_chars',
                'type', 'string',
                'label', 'Snippet character budget',
                'default', '1500'
        ),
        JSON_OBJECT(
                'key', 'description',
                'type', 'string',
                'label', 'Tool description (leave empty to use the built-in Thai description)',
                'default', ''
        )
    )
WHERE id = 'SYSTEM_PLUGIN_WEB_SEARCH';

-- Agents that already had this plugin: metaso is no longer supported, switch to auto
-- and clear the old mk- key so it is not mistaken for a Tavily key
UPDATE `ai_agent_plugin_mapping`
SET param_info = JSON_SET(param_info, '$.provider', 'auto')
WHERE plugin_id = 'SYSTEM_PLUGIN_WEB_SEARCH'
  AND JSON_UNQUOTE(JSON_EXTRACT(param_info, '$.provider')) = 'metaso';

UPDATE `ai_agent_plugin_mapping`
SET param_info = JSON_SET(param_info, '$.api_key', '')
WHERE plugin_id = 'SYSTEM_PLUGIN_WEB_SEARCH'
  AND JSON_UNQUOTE(JSON_EXTRACT(param_info, '$.api_key')) LIKE 'mk-%';
