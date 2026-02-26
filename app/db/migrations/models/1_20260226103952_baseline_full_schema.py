from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `auth_accounts` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `provider` VARCHAR(50) NOT NULL,
    `provider_user_id` VARCHAR(255),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_auth_accoun_provide_0c6510` (`provider`, `provider_user_id`),
    CONSTRAINT `fk_auth_acc_users_89fd16ec` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `patients` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `display_name` VARCHAR(100),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `owner_user_id` BIGINT NOT NULL,
    `user_id` BIGINT UNIQUE,
    CONSTRAINT `fk_patients_users_bc0d086e` FOREIGN KEY (`owner_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_patients_users_90e23b31` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `caregiver_patient_links` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `status` VARCHAR(30) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `revoked_at` DATETIME(6),
    `caregiver_user_id` BIGINT NOT NULL,
    `patient_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_caregiver_p_caregiv_a5c37c` (`caregiver_user_id`, `patient_id`),
    CONSTRAINT `fk_caregive_users_cd714b05` FOREIGN KEY (`caregiver_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_caregive_patients_e0d7e74d` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `chat_sessions` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `mode` VARCHAR(30),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT,
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_chat_ses_patients_6c9ad11b` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_chat_ses_users_520002c0` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_chat_sessio_user_id_1e4c0d` (`user_id`, `created_at`),
    KEY `idx_chat_sessio_patient_e4c386` (`patient_id`, `created_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `chat_messages` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `role` VARCHAR(20) NOT NULL,
    `content` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `session_id` BIGINT NOT NULL,
    CONSTRAINT `fk_chat_mes_chat_ses_0d4a2737` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE CASCADE,
    KEY `idx_chat_messag_session_fb3c4b` (`session_id`, `created_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `codes` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `group_code` VARCHAR(100) NOT NULL,
    `code` VARCHAR(100) NOT NULL,
    `value` VARCHAR(100) NOT NULL,
    `display_name` VARCHAR(100) NOT NULL,
    `description` LONGTEXT,
    `sort_order` INT NOT NULL DEFAULT 0,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    UNIQUE KEY `uid_codes_group_c_0c1e48` (`group_code`, `code`),
    UNIQUE KEY `uid_codes_group_c_5d8212` (`group_code`, `value`),
    KEY `idx_codes_group_c_f191ea` (`group_code`, `is_active`, `sort_order`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `code_groups` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `group_code` VARCHAR(100) NOT NULL UNIQUE,
    `group_name` VARCHAR(100) NOT NULL,
    `description` LONGTEXT,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `documents` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `file_url` VARCHAR(500) NOT NULL,
    `original_filename` VARCHAR(255),
    `file_type` VARCHAR(30),
    `file_size` BIGINT,
    `checksum` VARCHAR(255),
    `status` VARCHAR(30) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `deleted_at` DATETIME(6),
    `patient_id` BIGINT NOT NULL,
    `uploaded_by_user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_document_patients_7f26fcee` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_document_users_425860e1` FOREIGN KEY (`uploaded_by_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_documents_patient_4027bf` (`patient_id`, `created_at`),
    KEY `idx_documents_uploade_32177e` (`uploaded_by_user_id`, `created_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `drug_catalog` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `mfds_item_seq` VARCHAR(100) UNIQUE,
    `name` VARCHAR(255) NOT NULL,
    `manufacturer` VARCHAR(255),
    `ingredients` LONGTEXT,
    `warnings` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_drug_catalo_name_89ccbe` (`name`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `drug_info_cache` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `mfds_item_seq` VARCHAR(100) UNIQUE,
    `drug_name_display` VARCHAR(255),
    `manufacturer` VARCHAR(255),
    `efficacy` LONGTEXT,
    `dosage_info` LONGTEXT,
    `precautions` LONGTEXT,
    `interactions` LONGTEXT,
    `side_effects` LONGTEXT,
    `storage_method` VARCHAR(255),
    `expires_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_drug_info_c_expires_c0c53d` (`expires_at`),
    KEY `idx_drug_info_c_drug_na_823cfa` (`drug_name_display`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `dur_checks` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `trigger_type` VARCHAR(50) NOT NULL,
    `status` VARCHAR(30) NOT NULL,
    `error_code` VARCHAR(100),
    `error_message` LONGTEXT,
    `started_at` DATETIME(6),
    `finished_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL,
    `triggered_by_user_id` BIGINT,
    CONSTRAINT `fk_dur_chec_patients_688e35da` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_dur_chec_users_38350555` FOREIGN KEY (`triggered_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    KEY `idx_dur_checks_patient_b5f5a4` (`patient_id`, `created_at`),
    KEY `idx_dur_checks_status_f84123` (`status`, `created_at`),
    KEY `idx_dur_checks_trigger_eb0d2e` (`trigger_type`, `created_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `patient_meds` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `source_document_id` BIGINT,
    `source_ocr_job_id` BIGINT,
    `source_extracted_med_id` BIGINT,
    `display_name` VARCHAR(255) NOT NULL,
    `dosage` VARCHAR(255),
    `route` VARCHAR(100),
    `notes` LONGTEXT,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `confirmed_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `drug_catalog_id` BIGINT,
    `drug_info_cache_id` BIGINT,
    `patient_id` BIGINT NOT NULL,
    CONSTRAINT `fk_patient__drug_cat_4a06997b` FOREIGN KEY (`drug_catalog_id`) REFERENCES `drug_catalog` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_patient__drug_inf_e9295d6d` FOREIGN KEY (`drug_info_cache_id`) REFERENCES `drug_info_cache` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_patient__patients_c8e64c5e` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    KEY `idx_patient_med_patient_65e6f5` (`patient_id`, `is_active`),
    KEY `idx_patient_med_drug_ca_4857e8` (`drug_catalog_id`),
    KEY `idx_patient_med_drug_in_189f71` (`drug_info_cache_id`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `dur_alerts` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `alert_type` VARCHAR(50) NOT NULL,
    `level` VARCHAR(30) NOT NULL,
    `basis_json` LONGTEXT,
    `message` LONGTEXT,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `dur_check_id` BIGINT NOT NULL,
    `patient_id` BIGINT NOT NULL,
    `patient_med_id` BIGINT NOT NULL,
    `related_patient_med_id` BIGINT,
    CONSTRAINT `fk_dur_aler_dur_chec_f3559fcf` FOREIGN KEY (`dur_check_id`) REFERENCES `dur_checks` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_dur_aler_patients_0852b146` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_dur_aler_patient__4d0ba2eb` FOREIGN KEY (`patient_med_id`) REFERENCES `patient_meds` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_dur_aler_patient__2f7e0965` FOREIGN KEY (`related_patient_med_id`) REFERENCES `patient_meds` (`id`) ON DELETE SET NULL,
    KEY `idx_dur_alerts_patient_2c985b` (`patient_id`, `created_at`),
    KEY `idx_dur_alerts_patient_391f54` (`patient_med_id`, `created_at`),
    KEY `idx_dur_alerts_alert_t_0f33bb` (`alert_type`, `level`),
    KEY `idx_dur_alerts_dur_che_3808a4` (`dur_check_id`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `ocr_jobs` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `status` VARCHAR(30) NOT NULL,
    `retry_count` INT NOT NULL DEFAULT 0,
    `error_code` VARCHAR(100),
    `error_message` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `document_id` BIGINT NOT NULL,
    `patient_id` BIGINT NOT NULL,
    CONSTRAINT `fk_ocr_jobs_document_3e5e0a3f` FOREIGN KEY (`document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_ocr_jobs_patients_70933d1d` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    KEY `idx_ocr_jobs_patient_30a314` (`patient_id`, `status`),
    KEY `idx_ocr_jobs_documen_d7c30a` (`document_id`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `extracted_meds` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(255) NOT NULL,
    `dosage_text` VARCHAR(255),
    `frequency_text` VARCHAR(255),
    `duration_text` VARCHAR(255),
    `confidence` DECIMAL(5,4),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `ocr_job_id` BIGINT NOT NULL,
    `patient_id` BIGINT NOT NULL,
    CONSTRAINT `fk_extracte_ocr_jobs_dffe48f1` FOREIGN KEY (`ocr_job_id`) REFERENCES `ocr_jobs` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_extracte_patients_ac74f869` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    KEY `idx_extracted_m_patient_ae29c1` (`patient_id`),
    KEY `idx_extracted_m_ocr_job_b4a045` (`ocr_job_id`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `guides` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `status` VARCHAR(30) NOT NULL,
    `content` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL,
    `source_document_id` BIGINT,
    CONSTRAINT `fk_guides_patients_eaf6d3a2` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_guides_document_f3c5c365` FOREIGN KEY (`source_document_id`) REFERENCES `documents` (`id`) ON DELETE SET NULL,
    KEY `idx_guides_patient_a3fb33` (`patient_id`, `created_at`),
    KEY `idx_guides_status_309901` (`status`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `guide_feedback` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `rating` INT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `guide_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_guide_fe_guides_ca1c5bbf` FOREIGN KEY (`guide_id`) REFERENCES `guides` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_guide_fe_users_8b0361e8` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_guide_feedb_guide_i_dd1cc9` (`guide_id`, `created_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `guide_summaries` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `caregiver_summary` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `guide_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_guide_su_guides_71a250e5` FOREIGN KEY (`guide_id`) REFERENCES `guides` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `med_schedules` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `start_date` DATE,
    `end_date` DATE,
    `status` VARCHAR(30) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL,
    `patient_med_id` BIGINT NOT NULL,
    CONSTRAINT `fk_med_sche_patients_1a87dd03` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_med_sche_patient__21c24790` FOREIGN KEY (`patient_med_id`) REFERENCES `patient_meds` (`id`) ON DELETE CASCADE,
    KEY `idx_med_schedul_patient_4a5e58` (`patient_id`, `status`),
    KEY `idx_med_schedul_patient_334f7b` (`patient_med_id`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `med_schedule_times` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `time_of_day` TIME(6) NOT NULL,
    `days_of_week` VARCHAR(100),
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `schedule_id` BIGINT NOT NULL,
    CONSTRAINT `fk_med_sche_med_sche_969c03e5` FOREIGN KEY (`schedule_id`) REFERENCES `med_schedules` (`id`) ON DELETE CASCADE,
    KEY `idx_med_schedul_schedul_6df293` (`schedule_id`, `is_active`),
    KEY `idx_med_schedul_time_of_716e26` (`time_of_day`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `intake_logs` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `scheduled_at` DATETIME(6),
    `taken_at` DATETIME(6),
    `status` VARCHAR(30) NOT NULL,
    `note` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL,
    `patient_med_id` BIGINT NOT NULL,
    `recorded_by_user_id` BIGINT,
    `schedule_id` BIGINT,
    `schedule_time_id` BIGINT,
    CONSTRAINT `fk_intake_l_patients_c8b9c5a9` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_intake_l_patient__bf358c3a` FOREIGN KEY (`patient_med_id`) REFERENCES `patient_meds` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_intake_l_users_0d221710` FOREIGN KEY (`recorded_by_user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_intake_l_med_sche_e6efdcf2` FOREIGN KEY (`schedule_id`) REFERENCES `med_schedules` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_intake_l_med_sche_0d2a2dc9` FOREIGN KEY (`schedule_time_id`) REFERENCES `med_schedule_times` (`id`) ON DELETE SET NULL,
    KEY `idx_intake_logs_patient_53eb1f` (`patient_id`, `scheduled_at`),
    KEY `idx_intake_logs_patient_b2137a` (`patient_med_id`, `scheduled_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `invitation_codes` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(100) NOT NULL UNIQUE,
    `expires_at` DATETIME(6),
    `used_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL,
    CONSTRAINT `fk_invitati_patients_eefe4ef8` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `reminders` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `type` VARCHAR(30) NOT NULL,
    `channel` VARCHAR(30),
    `remind_at` DATETIME(6),
    `status` VARCHAR(30),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL,
    `schedule_id` BIGINT,
    `schedule_time_id` BIGINT,
    CONSTRAINT `fk_reminder_patients_34feade1` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_reminder_med_sche_cf5245f4` FOREIGN KEY (`schedule_id`) REFERENCES `med_schedules` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_reminder_med_sche_e7268a54` FOREIGN KEY (`schedule_time_id`) REFERENCES `med_schedule_times` (`id`) ON DELETE SET NULL,
    KEY `idx_reminders_patient_b51bb2` (`patient_id`, `remind_at`),
    KEY `idx_reminders_status_a71afa` (`status`, `remind_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `notifications` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `type` VARCHAR(50) NOT NULL,
    `title` VARCHAR(255),
    `body` LONGTEXT,
    `payload_json` LONGTEXT,
    `sent_at` DATETIME(6),
    `read_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT,
    `reminder_id` BIGINT,
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_notifica_patients_60b5cb95` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_notifica_reminder_d29f4431` FOREIGN KEY (`reminder_id`) REFERENCES `reminders` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_notifica_users_ca29871f` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_notificatio_user_id_8d780e` (`user_id`, `created_at`),
    KEY `idx_notificatio_user_id_87be33` (`user_id`, `read_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `ocr_raw_texts` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `raw_text` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `ocr_job_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_ocr_raw__ocr_jobs_90aa4b64` FOREIGN KEY (`ocr_job_id`) REFERENCES `ocr_jobs` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `patient_profiles` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `birth_year` INT,
    `sex` VARCHAR(20),
    `height_cm` DECIMAL(6,2),
    `weight_kg` DECIMAL(6,2),
    `bmi` DECIMAL(6,2),
    `conditions` LONGTEXT,
    `allergies` LONGTEXT,
    `notes` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_patient__patients_e4b7d852` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `patient_profile_history` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `snapshot_json` LONGTEXT NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL,
    CONSTRAINT `fk_patient__patients_31f97c9f` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `phone_verifications` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `phone` VARCHAR(20) NOT NULL,
    `token` VARCHAR(255) NOT NULL UNIQUE,
    `verified_at` DATETIME(6),
    `expires_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_phone_verif_phone_915268` (`phone`, `expires_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `refresh_tokens` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `token_hash` VARCHAR(255) NOT NULL,
    `expires_at` DATETIME(6) NOT NULL,
    `revoked_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_refresh__users_1c3fe0a4` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_refresh_tok_user_id_9490e0` (`user_id`, `expires_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `roles` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `name` VARCHAR(30) NOT NULL UNIQUE
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `user_devices` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `platform` VARCHAR(30),
    `push_token` VARCHAR(500) NOT NULL,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_user_dev_users_452e228e` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_user_device_user_id_80b679` (`user_id`, `is_active`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `user_roles` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `assigned_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `role_id` BIGINT NOT NULL,
    `user_id` BIGINT NOT NULL,
    UNIQUE KEY `uid_user_roles_user_id_63f1a8` (`user_id`, `role_id`),
    CONSTRAINT `fk_user_rol_roles_65d4d60a` FOREIGN KEY (`role_id`) REFERENCES `roles` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_user_rol_users_55397de2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4;
        ALTER TABLE `users` ADD `nickname` VARCHAR(50);
        ALTER TABLE `users` DROP COLUMN `last_login`;
        ALTER TABLE `users` DROP COLUMN `is_admin`;
        ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(50) NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD `last_login` DATETIME(6);
        ALTER TABLE `users` ADD `is_admin` BOOL NOT NULL DEFAULT 0;
        ALTER TABLE `users` DROP COLUMN `nickname`;
        ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(20) NOT NULL;
        DROP TABLE IF EXISTS `intake_logs`;
        DROP TABLE IF EXISTS `phone_verifications`;
        DROP TABLE IF EXISTS `guides`;
        DROP TABLE IF EXISTS `user_roles`;
        DROP TABLE IF EXISTS `caregiver_patient_links`;
        DROP TABLE IF EXISTS `patient_meds`;
        DROP TABLE IF EXISTS `roles`;
        DROP TABLE IF EXISTS `ocr_jobs`;
        DROP TABLE IF EXISTS `dur_alerts`;
        DROP TABLE IF EXISTS `dur_checks`;
        DROP TABLE IF EXISTS `patient_profile_history`;
        DROP TABLE IF EXISTS `ocr_raw_texts`;
        DROP TABLE IF EXISTS `guide_summaries`;
        DROP TABLE IF EXISTS `med_schedules`;
        DROP TABLE IF EXISTS `guide_feedback`;
        DROP TABLE IF EXISTS `drug_info_cache`;
        DROP TABLE IF EXISTS `codes`;
        DROP TABLE IF EXISTS `refresh_tokens`;
        DROP TABLE IF EXISTS `auth_accounts`;
        DROP TABLE IF EXISTS `notifications`;
        DROP TABLE IF EXISTS `chat_sessions`;
        DROP TABLE IF EXISTS `med_schedule_times`;
        DROP TABLE IF EXISTS `chat_messages`;
        DROP TABLE IF EXISTS `drug_catalog`;
        DROP TABLE IF EXISTS `invitation_codes`;
        DROP TABLE IF EXISTS `patients`;
        DROP TABLE IF EXISTS `user_devices`;
        DROP TABLE IF EXISTS `reminders`;
        DROP TABLE IF EXISTS `patient_profiles`;
        DROP TABLE IF EXISTS `code_groups`;
        DROP TABLE IF EXISTS `documents`;
        DROP TABLE IF EXISTS `extracted_meds`;"""


MODELS_STATE = (
    "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"
)
