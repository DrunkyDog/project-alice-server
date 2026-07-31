-- liquibase formatted sql

-- changeset DrunkyDog:202607311600
-- News plugin switches from ChinaNews (get_news_from_chinanews) to Thai news (get_news_from_thai)
-- The provider id is kept so agents that already enabled this plugin keep their mapping
-- (ai_agent_plugin_mapping.plugin_id)
-- Defaults are literals on purpose: 202505292203 ends with
--   DELETE FROM sys_params WHERE param_code LIKE 'plugins.%'
-- so reading them back out of sys_params would write NULL defaults into the field list.

UPDATE `ai_model_provider`
SET provider_code = 'get_news_from_thai',
    name = 'Thai News',
    fields = JSON_ARRAY(
            JSON_OBJECT(
                    'key', 'default_rss_url',
                    'type', 'string',
                    'label', 'Default RSS feed (general news)',
                    'default', 'https://www.thairath.co.th/rss/news'
            ),
            JSON_OBJECT(
                    'key', 'economy_rss_url',
                    'type', 'string',
                    'label', 'Business RSS feed',
                    'default', 'https://www.matichon.co.th/economy/feed'
            ),
            JSON_OBJECT(
                    'key', 'world_rss_url',
                    'type', 'string',
                    'label', 'World RSS feed',
                    'default', 'https://www.matichon.co.th/foreign/feed'
            ),
            JSON_OBJECT(
                    'key', 'sport_rss_url',
                    'type', 'string',
                    'label', 'Sport RSS feed',
                    'default', 'https://www.thairath.co.th/rss/sport'
            ),
            JSON_OBJECT(
                    'key', 'entertain_rss_url',
                    'type', 'string',
                    'label', 'Entertainment RSS feed',
                    'default', 'https://www.thairath.co.th/rss/entertain'
            ),
            JSON_OBJECT(
                    'key', 'local_rss_url',
                    'type', 'string',
                    'label', 'Local RSS feed',
                    'default', 'https://www.matichon.co.th/local/feed'
            ),
            JSON_OBJECT(
                    'key', 'tech_rss_url',
                    'type', 'string',
                    'label', 'Technology RSS feed',
                    'default', 'https://www.blognone.com/atom.xml'
            )
    )
WHERE id = 'SYSTEM_PLUGIN_NEWS_CHINANEWS';

-- Agents that already had this plugin keep their old param_info, and an agent-level value
-- overrides the built-in Thai feeds. Point the default feed at Thai news and drop the
-- ChinaNews-only category keys.
UPDATE `ai_agent_plugin_mapping`
SET param_info = JSON_SET(param_info, '$.default_rss_url', 'https://www.thairath.co.th/rss/news')
WHERE plugin_id = 'SYSTEM_PLUGIN_NEWS_CHINANEWS'
  AND JSON_UNQUOTE(JSON_EXTRACT(param_info, '$.default_rss_url')) LIKE '%chinanews.com.cn%';

UPDATE `ai_agent_plugin_mapping`
SET param_info = JSON_REMOVE(param_info, '$.society_rss_url', '$.finance_rss_url')
WHERE plugin_id = 'SYSTEM_PLUGIN_NEWS_CHINANEWS'
  AND (JSON_EXTRACT(param_info, '$.society_rss_url') IS NOT NULL
       OR JSON_EXTRACT(param_info, '$.finance_rss_url') IS NOT NULL);

-- world_rss_url exists in both the old and the new field list, so only replace it when it
-- still points at ChinaNews
UPDATE `ai_agent_plugin_mapping`
SET param_info = JSON_SET(param_info, '$.world_rss_url', 'https://www.matichon.co.th/foreign/feed')
WHERE plugin_id = 'SYSTEM_PLUGIN_NEWS_CHINANEWS'
  AND JSON_UNQUOTE(JSON_EXTRACT(param_info, '$.world_rss_url')) LIKE '%chinanews.com.cn%';
