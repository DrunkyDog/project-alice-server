-- liquibase formatted sql

-- changeset DrunkyDog:202607311400
-- Register the live clock plugin (get_current_time) with a configurable timezone
SET @data_exists = (SELECT COUNT(*) FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_CURRENT_TIME');
SET @sql = IF(@data_exists = 0,
    'INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES (''SYSTEM_PLUGIN_CURRENT_TIME'', ''Plugin'', ''get_current_time'', ''Live Clock'', ''[{\"key\": \"timezone\", \"type\": \"string\", \"label\": \"Timezone (IANA name, e.g. Asia/Bangkok)\", \"default\": \"Asia/Bangkok\", \"editing\": false, \"selected\": false}]'', 15, 0, NOW(), 0, NOW())',
    'SELECT ''data already exists, skip'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
