from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `auth_accounts` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `provider` VARCHAR(20) NOT NULL,
    `provider_user_id` VARCHAR(120),
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
    CONSTRAINT `fk_patients_users_90e23b31` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
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
    CONSTRAINT `fk_chat_ses_patients_6c9ad11b` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
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
        CREATE TABLE IF NOT EXISTS `code_groups` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `group_code` VARCHAR(20) NOT NULL UNIQUE,
    `group_name` VARCHAR(100) NOT NULL,
    `description` LONGTEXT,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `codes` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(50) NOT NULL,
    `value` VARCHAR(50) NOT NULL,
    `display_name` VARCHAR(100) NOT NULL,
    `description` LONGTEXT,
    `sort_order` INT NOT NULL DEFAULT 0,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `group_code_id` VARCHAR(20) NOT NULL,
    UNIQUE KEY `uid_codes_group_c_0372a2` (`group_code_id`, `code`),
    UNIQUE KEY `uid_codes_group_c_b0eba2` (`group_code_id`, `value`),
    CONSTRAINT `fk_codes_code_gro_d72aee53` FOREIGN KEY (`group_code_id`) REFERENCES `code_groups` (`group_code`) ON DELETE CASCADE,
    KEY `idx_codes_group_c_48c083` (`group_code_id`, `is_active`, `sort_order`)
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
    `mfds_item_seq` VARCHAR(50) UNIQUE,
    `name` VARCHAR(200) NOT NULL,
    `manufacturer` VARCHAR(150),
    `ingredients` LONGTEXT,
    `warnings` LONGTEXT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_drug_catalo_name_89ccbe` (`name`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `drug_info_cache` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `mfds_item_seq` VARCHAR(50) UNIQUE,
    `drug_name_display` VARCHAR(200),
    `manufacturer` VARCHAR(150),
    `efficacy` LONGTEXT,
    `dosage_info` LONGTEXT,
    `precautions` LONGTEXT,
    `interactions` LONGTEXT,
    `side_effects` LONGTEXT,
    `storage_method` VARCHAR(200),
    `expires_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    KEY `idx_drug_info_c_expires_c0c53d` (`expires_at`),
    KEY `idx_drug_info_c_drug_na_823cfa` (`drug_name_display`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `dur_checks` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `trigger_type` VARCHAR(30) NOT NULL,
    `status` VARCHAR(30) NOT NULL,
    `error_code` VARCHAR(100),
    `error_message` LONGTEXT,
    `started_at` DATETIME(6),
    `finished_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT NOT NULL,
    `triggered_by_user_id` BIGINT,
    CONSTRAINT `fk_dur_chec_patients_688e35da` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_dur_chec_users_38350555` FOREIGN KEY (`triggered_by_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    KEY `idx_dur_checks_patient_b5f5a4` (`patient_id`, `created_at`),
    KEY `idx_dur_checks_status_f84123` (`status`, `created_at`),
    KEY `idx_dur_checks_trigger_eb0d2e` (`trigger_type`, `created_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `patient_meds` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `display_name` VARCHAR(200) NOT NULL,
    `dosage` VARCHAR(200),
    `route` VARCHAR(100),
    `notes` LONGTEXT,
    `is_active` BOOL NOT NULL DEFAULT 1,
    `confirmed_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `drug_catalog_id` BIGINT,
    `drug_info_cache_id` BIGINT,
    `patient_id` BIGINT NOT NULL,
    `source_document_id` BIGINT,
    `source_extracted_med_id` BIGINT,
    `source_ocr_job_id` BIGINT,
    CONSTRAINT `fk_patient__drug_cat_4a06997b` FOREIGN KEY (`drug_catalog_id`) REFERENCES `drug_catalog` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_patient__drug_inf_e9295d6d` FOREIGN KEY (`drug_info_cache_id`) REFERENCES `drug_info_cache` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_patient__patients_c8e64c5e` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_patient__document_53214333` FOREIGN KEY (`source_document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_patient__extracte_0a124ded` FOREIGN KEY (`source_extracted_med_id`) REFERENCES `extracted_meds` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_patient__ocr_jobs_e56f4bf6` FOREIGN KEY (`source_ocr_job_id`) REFERENCES `ocr_jobs` (`id`) ON DELETE CASCADE,
    KEY `idx_patient_med_patient_65e6f5` (`patient_id`, `is_active`),
    KEY `idx_patient_med_drug_ca_4857e8` (`drug_catalog_id`),
    KEY `idx_patient_med_drug_in_189f71` (`drug_info_cache_id`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `dur_alerts` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `alert_type` VARCHAR(30) NOT NULL,
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
    CONSTRAINT `fk_dur_aler_patient__2f7e0965` FOREIGN KEY (`related_patient_med_id`) REFERENCES `patient_meds` (`id`) ON DELETE CASCADE,
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
    `name` VARCHAR(150) NOT NULL,
    `dosage_text` VARCHAR(200),
    `frequency_text` VARCHAR(200),
    `duration_text` VARCHAR(200),
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
    CONSTRAINT `fk_guides_document_f3c5c365` FOREIGN KEY (`source_document_id`) REFERENCES `documents` (`id`) ON DELETE CASCADE,
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
    `days_of_week` VARCHAR(40),
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
    CONSTRAINT `fk_intake_l_users_0d221710` FOREIGN KEY (`recorded_by_user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_intake_l_med_sche_e6efdcf2` FOREIGN KEY (`schedule_id`) REFERENCES `med_schedules` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_intake_l_med_sche_0d2a2dc9` FOREIGN KEY (`schedule_time_id`) REFERENCES `med_schedule_times` (`id`) ON DELETE CASCADE,
    KEY `idx_intake_logs_patient_53eb1f` (`patient_id`, `scheduled_at`),
    KEY `idx_intake_logs_patient_b2137a` (`patient_med_id`, `scheduled_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `invitation_codes` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `code` VARCHAR(50) NOT NULL UNIQUE,
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
    CONSTRAINT `fk_reminder_med_sche_cf5245f4` FOREIGN KEY (`schedule_id`) REFERENCES `med_schedules` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_reminder_med_sche_e7268a54` FOREIGN KEY (`schedule_time_id`) REFERENCES `med_schedule_times` (`id`) ON DELETE CASCADE,
    KEY `idx_reminders_patient_b51bb2` (`patient_id`, `remind_at`),
    KEY `idx_reminders_status_a71afa` (`status`, `remind_at`)
) CHARACTER SET utf8mb4;
        CREATE TABLE IF NOT EXISTS `notifications` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `type` VARCHAR(30) NOT NULL,
    `title` VARCHAR(200),
    `body` LONGTEXT,
    `payload_json` LONGTEXT,
    `sent_at` DATETIME(6),
    `read_at` DATETIME(6),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `patient_id` BIGINT,
    `reminder_id` BIGINT,
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_notifica_patients_60b5cb95` FOREIGN KEY (`patient_id`) REFERENCES `patients` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_notifica_reminder_d29f4431` FOREIGN KEY (`reminder_id`) REFERENCES `reminders` (`id`) ON DELETE CASCADE,
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
    `bmi` DECIMAL(5,2),
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
    `phone` VARCHAR(30) NOT NULL,
    `token` VARCHAR(100) NOT NULL UNIQUE,
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
    `platform` VARCHAR(20),
    `push_token` VARCHAR(300) NOT NULL,
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
        ALTER TABLE `users` MODIFY COLUMN `birth_date` DATE NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `password_hash` VARCHAR(128);
        ALTER TABLE `users` MODIFY COLUMN `password_hash` VARCHAR(128);
        ALTER TABLE `users` MODIFY COLUMN `phone` VARCHAR(20) NOT NULL;
        ALTER TABLE `users` ADD UNIQUE INDEX `email` (`email`);
        ALTER TABLE `users` ADD UNIQUE INDEX `phone` (`phone`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP INDEX `phone`;
        ALTER TABLE `users` DROP INDEX `email`;
        ALTER TABLE `users` DROP COLUMN `nickname`;
        ALTER TABLE `users` MODIFY COLUMN `birthday` DATE NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `hashed_password` VARCHAR(128) NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `hashed_password` VARCHAR(128) NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `phone_number` VARCHAR(11) NOT NULL;
        DROP TABLE IF EXISTS `chat_sessions`;
        DROP TABLE IF EXISTS `user_devices`;
        DROP TABLE IF EXISTS `dur_alerts`;
        DROP TABLE IF EXISTS `notifications`;
        DROP TABLE IF EXISTS `ocr_jobs`;
        DROP TABLE IF EXISTS `dur_checks`;
        DROP TABLE IF EXISTS `intake_logs`;
        DROP TABLE IF EXISTS `guides`;
        DROP TABLE IF EXISTS `roles`;
        DROP TABLE IF EXISTS `patients`;
        DROP TABLE IF EXISTS `user_roles`;
        DROP TABLE IF EXISTS `ocr_raw_texts`;
        DROP TABLE IF EXISTS `patient_meds`;
        DROP TABLE IF EXISTS `reminders`;
        DROP TABLE IF EXISTS `guide_summaries`;
        DROP TABLE IF EXISTS `chat_messages`;
        DROP TABLE IF EXISTS `patient_profiles`;
        DROP TABLE IF EXISTS `caregiver_patient_links`;
        DROP TABLE IF EXISTS `drug_catalog`;
        DROP TABLE IF EXISTS `med_schedules`;
        DROP TABLE IF EXISTS `auth_accounts`;
        DROP TABLE IF EXISTS `drug_info_cache`;
        DROP TABLE IF EXISTS `code_groups`;
        DROP TABLE IF EXISTS `codes`;
        DROP TABLE IF EXISTS `invitation_codes`;
        DROP TABLE IF EXISTS `refresh_tokens`;
        DROP TABLE IF EXISTS `documents`;
        DROP TABLE IF EXISTS `extracted_meds`;
        DROP TABLE IF EXISTS `guide_feedback`;
        DROP TABLE IF EXISTS `phone_verifications`;
        DROP TABLE IF EXISTS `patient_profile_history`;
        DROP TABLE IF EXISTS `med_schedule_times`;"""


MODELS_STATE = (
    "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"
)
