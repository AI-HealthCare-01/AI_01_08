from tortoise import fields, models


class Guide(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="guides", on_delete=fields.CASCADE)
    source_document = fields.ForeignKeyField("models.Document", related_name="guides", null=True, on_delete=fields.SET_NULL)
    status = fields.CharField(max_length=30)
    content = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "guides"
        indexes = (("patient_id", "created_at"), ("status",))


class GuideSummary(models.Model):
    id = fields.BigIntField(primary_key=True)
    guide = fields.OneToOneField("models.Guide", related_name="summary", on_delete=fields.CASCADE)
    caregiver_summary = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "guide_summaries"


class GuideFeedback(models.Model):
    id = fields.BigIntField(primary_key=True)
    guide = fields.ForeignKeyField("models.Guide", related_name="feedbacks", on_delete=fields.CASCADE)
    user = fields.ForeignKeyField("models.User", related_name="guide_feedbacks", on_delete=fields.CASCADE)
    rating = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "guide_feedback"
        indexes = (("guide_id", "created_at"),)
