from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `notification_settings`
        ADD COLUMN `hospital_schedule_reminder` BOOL NOT NULL DEFAULT 1;
    """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `notification_settings`
        DROP COLUMN `hospital_schedule_reminder`;
    """
