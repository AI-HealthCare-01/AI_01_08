from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `auth_accounts` MODIFY COLUMN `provider_user_id` VARCHAR(120);
        ALTER TABLE `auth_accounts` MODIFY COLUMN `provider` VARCHAR(20) NOT NULL;
        ALTER TABLE `codes` ADD `group_code_id` VARCHAR(20) NOT NULL;
        ALTER TABLE `codes` DROP COLUMN `group_code`;
        ALTER TABLE `codes` MODIFY COLUMN `code` VARCHAR(50) NOT NULL;
        ALTER TABLE `codes` MODIFY COLUMN `value` VARCHAR(50) NOT NULL;
        ALTER TABLE `code_groups` MODIFY COLUMN `group_code` VARCHAR(20) NOT NULL;
        ALTER TABLE `phone_verifications` MODIFY COLUMN `phone` VARCHAR(30) NOT NULL;
        ALTER TABLE `phone_verifications` MODIFY COLUMN `token` VARCHAR(100) NOT NULL;
        ALTER TABLE `roles` ADD `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6);
        ALTER TABLE `roles` ADD `description` VARCHAR(255);
        ALTER TABLE `roles` ADD `code` VARCHAR(9) NOT NULL UNIQUE;
        ALTER TABLE `roles` ADD `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6);
        ALTER TABLE `users` MODIFY COLUMN `password_hash` VARCHAR(128);
        ALTER TABLE `users` MODIFY COLUMN `password_hash` VARCHAR(128);
        ALTER TABLE `users` MODIFY COLUMN `birth_date` DATE NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `phone` VARCHAR(20) NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(20) NOT NULL;
        ALTER TABLE `codes` ADD CONSTRAINT `fk_codes_code_gro_7dbe3732` FOREIGN KEY (`group_code_id`) REFERENCES `code_groups` (`id`) ON DELETE CASCADE;
        ALTER TABLE `users` ADD UNIQUE INDEX `phone` (`phone`);
        ALTER TABLE `users` ADD UNIQUE INDEX `email` (`email`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP INDEX `email`;
        ALTER TABLE `users` DROP INDEX `phone`;
        ALTER TABLE `roles` DROP INDEX `code`;
        ALTER TABLE `codes` DROP FOREIGN KEY `fk_codes_code_gro_7dbe3732`;
        ALTER TABLE `codes` ADD `group_code` VARCHAR(100) NOT NULL;
        ALTER TABLE `codes` DROP COLUMN `group_code_id`;
        ALTER TABLE `codes` MODIFY COLUMN `code` VARCHAR(100) NOT NULL;
        ALTER TABLE `codes` MODIFY COLUMN `value` VARCHAR(100) NOT NULL;
        ALTER TABLE `roles` DROP COLUMN `updated_at`;
        ALTER TABLE `roles` DROP COLUMN `description`;
        ALTER TABLE `roles` DROP COLUMN `code`;
        ALTER TABLE `roles` DROP COLUMN `created_at`;
        ALTER TABLE `users` MODIFY COLUMN `hashed_password` VARCHAR(128) NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `hashed_password` VARCHAR(128) NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `birthday` DATE NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `phone_number` VARCHAR(11) NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(50) NOT NULL;
        ALTER TABLE `code_groups` MODIFY COLUMN `group_code` VARCHAR(100) NOT NULL;
        ALTER TABLE `auth_accounts` MODIFY COLUMN `provider_user_id` VARCHAR(255);
        ALTER TABLE `auth_accounts` MODIFY COLUMN `provider` VARCHAR(50) NOT NULL;
        ALTER TABLE `phone_verifications` MODIFY COLUMN `phone` VARCHAR(20) NOT NULL;
        ALTER TABLE `phone_verifications` MODIFY COLUMN `token` VARCHAR(255) NOT NULL;"""


MODELS_STATE = (
    "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"
    "gBNf10WBE1ZlKbnrL9/H/k6Qxq"
)
