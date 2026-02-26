from tortoise import fields, models


class ChatSession(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="chat_sessions", on_delete=fields.CASCADE)
    patient = fields.ForeignKeyField("models.Patient", related_name="chat_sessions", null=True, on_delete=fields.SET_NULL)
    mode = fields.CharField(max_length=30, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_sessions"
        indexes = (("user_id", "created_at"), ("patient_id", "created_at"))


class ChatMessage(models.Model):
    id = fields.BigIntField(primary_key=True)
    session = fields.ForeignKeyField("models.ChatSession", related_name="messages", on_delete=fields.CASCADE)
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"
        indexes = (("session_id", "created_at"),)
