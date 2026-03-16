from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `user_settings` (
            `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
            `dark_mode` BOOL NOT NULL DEFAULT 0,
            `language` VARCHAR(10) NOT NULL DEFAULT 'ko',
            `push_notifications` BOOL NOT NULL DEFAULT 1,
            `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
            `user_id` BIGINT NOT NULL UNIQUE,
            CONSTRAINT `fk_user_set_users_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
        ) CHARACTER SET utf8mb4;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `user_settings`;
    """
