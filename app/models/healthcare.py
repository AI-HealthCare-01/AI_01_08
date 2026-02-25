from tortoise import fields, models


class CodeGroup(models.Model):
    id = fields.BigIntField(primary_key=True)
    group_code = fields.CharField(max_length=20, unique=True)
    group_name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "code_groups"


class Code(models.Model):
    id = fields.BigIntField(primary_key=True)
    group_code = fields.ForeignKeyField("models.CodeGroup", to_field="group_code", related_name="codes")
    code = fields.CharField(max_length=50)
    value = fields.CharField(max_length=50)
    display_name = fields.CharField(max_length=100)
    description = fields.TextField(null=True)
    sort_order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "codes"
        unique_together = (("group_code", "code"), ("group_code", "value"))
        indexes = [("group_code", "is_active", "sort_order")]


class PhoneVerification(models.Model):
    id = fields.BigIntField(primary_key=True)
    phone = fields.CharField(max_length=30)
    token = fields.CharField(max_length=100, unique=True)
    verified_at = fields.DatetimeField(null=True)
    expires_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "phone_verifications"
        indexes = [("phone", "expires_at")]


class AuthAccount(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="auth_accounts")
    provider = fields.CharField(max_length=20)
    provider_user_id = fields.CharField(max_length=120, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "auth_accounts"
        unique_together = (("provider", "provider_user_id"),)


class RefreshToken(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="refresh_tokens")
    token_hash = fields.CharField(max_length=255)
    expires_at = fields.DatetimeField()
    revoked_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "refresh_tokens"
        indexes = [("user_id", "expires_at")]


class Role(models.Model):
    id = fields.BigIntField(primary_key=True)
    name = fields.CharField(max_length=30, unique=True)

    class Meta:
        table = "roles"


class UserRole(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="user_roles")
    role = fields.ForeignKeyField("models.Role", related_name="user_roles")
    assigned_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_roles"
        unique_together = (("user", "role"),)


class Patient(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.OneToOneField("models.User", null=True, related_name="patient_profile_owner")
    owner_user = fields.ForeignKeyField("models.User", related_name="owned_patients")
    display_name = fields.CharField(max_length=100, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "patients"


class PatientProfile(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.OneToOneField("models.Patient", related_name="profile")
    birth_year = fields.IntField(null=True)
    sex = fields.CharField(max_length=20, null=True)
    height_cm = fields.DecimalField(max_digits=6, decimal_places=2, null=True)
    weight_kg = fields.DecimalField(max_digits=6, decimal_places=2, null=True)
    bmi = fields.DecimalField(max_digits=5, decimal_places=2, null=True)
    conditions = fields.TextField(null=True)
    allergies = fields.TextField(null=True)
    notes = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "patient_profiles"


class PatientProfileHistory(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="profile_history")
    snapshot_json = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "patient_profile_history"


class InvitationCode(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="invitation_codes")
    code = fields.CharField(max_length=50, unique=True)
    expires_at = fields.DatetimeField(null=True)
    used_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "invitation_codes"


class CaregiverPatientLink(models.Model):
    id = fields.BigIntField(primary_key=True)
    caregiver_user = fields.ForeignKeyField("models.User", related_name="caregiver_links")
    patient = fields.ForeignKeyField("models.Patient", related_name="caregiver_links")
    status = fields.CharField(max_length=30)
    created_at = fields.DatetimeField(auto_now_add=True)
    revoked_at = fields.DatetimeField(null=True)

    class Meta:
        table = "caregiver_patient_links"
        unique_together = (("caregiver_user", "patient"),)


class Document(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="documents")
    uploaded_by_user = fields.ForeignKeyField("models.User", related_name="uploaded_documents")
    file_url = fields.CharField(max_length=500)
    original_filename = fields.CharField(max_length=255, null=True)
    file_type = fields.CharField(max_length=30, null=True)
    file_size = fields.BigIntField(null=True)
    checksum = fields.CharField(max_length=255, null=True)
    status = fields.CharField(max_length=30)
    created_at = fields.DatetimeField(auto_now_add=True)
    deleted_at = fields.DatetimeField(null=True)

    class Meta:
        table = "documents"
        indexes = [("patient_id", "created_at"), ("uploaded_by_user_id", "created_at")]


class OcrJob(models.Model):
    id = fields.BigIntField(primary_key=True)
    document = fields.ForeignKeyField("models.Document", related_name="ocr_jobs")
    patient = fields.ForeignKeyField("models.Patient", related_name="ocr_jobs")
    status = fields.CharField(max_length=30)
    retry_count = fields.IntField(default=0)
    error_code = fields.CharField(max_length=100, null=True)
    error_message = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "ocr_jobs"
        indexes = [("patient_id", "status"), ("document_id",)]


class OcrRawText(models.Model):
    id = fields.BigIntField(primary_key=True)
    ocr_job = fields.OneToOneField("models.OcrJob", related_name="raw_text")
    raw_text = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "ocr_raw_texts"


class ExtractedMed(models.Model):
    id = fields.BigIntField(primary_key=True)
    ocr_job = fields.ForeignKeyField("models.OcrJob", related_name="extracted_meds")
    patient = fields.ForeignKeyField("models.Patient", related_name="extracted_meds")
    name = fields.CharField(max_length=150)
    dosage_text = fields.CharField(max_length=200, null=True)
    frequency_text = fields.CharField(max_length=200, null=True)
    duration_text = fields.CharField(max_length=200, null=True)
    confidence = fields.DecimalField(max_digits=5, decimal_places=4, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "extracted_meds"
        indexes = [("patient_id",), ("ocr_job_id",)]


class DrugCatalog(models.Model):
    id = fields.BigIntField(primary_key=True)
    mfds_item_seq = fields.CharField(max_length=50, unique=True, null=True)
    name = fields.CharField(max_length=200)
    manufacturer = fields.CharField(max_length=150, null=True)
    ingredients = fields.TextField(null=True)
    warnings = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "drug_catalog"
        indexes = [("name",)]


class DrugInfoCache(models.Model):
    id = fields.BigIntField(primary_key=True)
    mfds_item_seq = fields.CharField(max_length=50, unique=True, null=True)
    drug_name_display = fields.CharField(max_length=200, null=True)
    manufacturer = fields.CharField(max_length=150, null=True)
    efficacy = fields.TextField(null=True)
    dosage_info = fields.TextField(null=True)
    precautions = fields.TextField(null=True)
    interactions = fields.TextField(null=True)
    side_effects = fields.TextField(null=True)
    storage_method = fields.CharField(max_length=200, null=True)
    expires_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "drug_info_cache"
        indexes = [("expires_at",), ("drug_name_display",)]


class PatientMed(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="patient_meds")
    source_document = fields.ForeignKeyField("models.Document", related_name="patient_meds", null=True)
    source_ocr_job = fields.ForeignKeyField("models.OcrJob", related_name="patient_meds", null=True)
    source_extracted_med = fields.ForeignKeyField("models.ExtractedMed", related_name="patient_meds", null=True)
    drug_catalog = fields.ForeignKeyField("models.DrugCatalog", related_name="patient_meds", null=True)
    drug_info_cache = fields.ForeignKeyField("models.DrugInfoCache", related_name="patient_meds", null=True)
    display_name = fields.CharField(max_length=200)
    dosage = fields.CharField(max_length=200, null=True)
    route = fields.CharField(max_length=100, null=True)
    notes = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    confirmed_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "patient_meds"
        indexes = [("patient_id", "is_active"), ("drug_catalog_id",), ("drug_info_cache_id",)]


class MedSchedule(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="med_schedules")
    patient_med = fields.ForeignKeyField("models.PatientMed", related_name="med_schedules")
    start_date = fields.DateField(null=True)
    end_date = fields.DateField(null=True)
    status = fields.CharField(max_length=30)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "med_schedules"
        indexes = [("patient_id", "status"), ("patient_med_id",)]


class MedScheduleTime(models.Model):
    id = fields.BigIntField(primary_key=True)
    schedule = fields.ForeignKeyField("models.MedSchedule", related_name="times")
    time_of_day = fields.TimeField()
    days_of_week = fields.CharField(max_length=40, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "med_schedule_times"
        indexes = [("schedule_id", "is_active"), ("time_of_day",)]


class IntakeLog(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="intake_logs")
    schedule = fields.ForeignKeyField("models.MedSchedule", related_name="intake_logs", null=True)
    schedule_time = fields.ForeignKeyField("models.MedScheduleTime", related_name="intake_logs", null=True)
    patient_med = fields.ForeignKeyField("models.PatientMed", related_name="intake_logs")
    recorded_by_user = fields.ForeignKeyField("models.User", related_name="recorded_intake_logs", null=True)
    scheduled_at = fields.DatetimeField(null=True)
    taken_at = fields.DatetimeField(null=True)
    status = fields.CharField(max_length=30)
    note = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "intake_logs"
        indexes = [("patient_id", "scheduled_at"), ("patient_med_id", "scheduled_at")]


class Reminder(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="reminders")
    schedule = fields.ForeignKeyField("models.MedSchedule", related_name="reminders", null=True)
    schedule_time = fields.ForeignKeyField("models.MedScheduleTime", related_name="reminders", null=True)
    type = fields.CharField(max_length=30)
    channel = fields.CharField(max_length=30, null=True)
    remind_at = fields.DatetimeField(null=True)
    status = fields.CharField(max_length=30, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "reminders"
        indexes = [("patient_id", "remind_at"), ("status", "remind_at")]


class UserDevice(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="devices")
    platform = fields.CharField(max_length=20, null=True)
    push_token = fields.CharField(max_length=300)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "user_devices"
        indexes = [("user_id", "is_active")]


class Notification(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="notifications")
    patient = fields.ForeignKeyField("models.Patient", related_name="notifications", null=True)
    reminder = fields.ForeignKeyField("models.Reminder", related_name="notifications", null=True)
    type = fields.CharField(max_length=30)
    title = fields.CharField(max_length=200, null=True)
    body = fields.TextField(null=True)
    payload_json = fields.TextField(null=True)
    sent_at = fields.DatetimeField(null=True)
    read_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "notifications"
        indexes = [("user_id", "created_at"), ("user_id", "read_at")]


class Guide(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="guides")
    source_document = fields.ForeignKeyField("models.Document", related_name="guides", null=True)
    status = fields.CharField(max_length=30)
    content = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "guides"
        indexes = [("patient_id", "created_at"), ("status",)]


class GuideSummary(models.Model):
    id = fields.BigIntField(primary_key=True)
    guide = fields.OneToOneField("models.Guide", related_name="summary")
    caregiver_summary = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "guide_summaries"


class GuideFeedback(models.Model):
    id = fields.BigIntField(primary_key=True)
    guide = fields.ForeignKeyField("models.Guide", related_name="feedbacks")
    user = fields.ForeignKeyField("models.User", related_name="guide_feedbacks")
    rating = fields.IntField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "guide_feedback"
        indexes = [("guide_id", "created_at")]


class ChatSession(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.ForeignKeyField("models.User", related_name="chat_sessions")
    patient = fields.ForeignKeyField("models.Patient", related_name="chat_sessions", null=True)
    mode = fields.CharField(max_length=30, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_sessions"
        indexes = [("user_id", "created_at"), ("patient_id", "created_at")]


class ChatMessage(models.Model):
    id = fields.BigIntField(primary_key=True)
    session = fields.ForeignKeyField("models.ChatSession", related_name="messages")
    role = fields.CharField(max_length=20)
    content = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"
        indexes = [("session_id", "created_at")]


class DurCheck(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="dur_checks")
    trigger_type = fields.CharField(max_length=30)
    triggered_by_user = fields.ForeignKeyField("models.User", related_name="dur_checks", null=True)
    status = fields.CharField(max_length=30)
    error_code = fields.CharField(max_length=100, null=True)
    error_message = fields.TextField(null=True)
    started_at = fields.DatetimeField(null=True)
    finished_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dur_checks"
        indexes = [("patient_id", "created_at"), ("status", "created_at"), ("trigger_type", "created_at")]


class DurAlert(models.Model):
    id = fields.BigIntField(primary_key=True)
    dur_check = fields.ForeignKeyField("models.DurCheck", related_name="alerts")
    patient = fields.ForeignKeyField("models.Patient", related_name="dur_alerts")
    patient_med = fields.ForeignKeyField("models.PatientMed", related_name="dur_alerts")
    related_patient_med = fields.ForeignKeyField(
        "models.PatientMed",
        related_name="related_dur_alerts",
        null=True,
    )
    alert_type = fields.CharField(max_length=30)
    level = fields.CharField(max_length=30)
    basis_json = fields.TextField(null=True)
    message = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "dur_alerts"
        indexes = [
            ("patient_id", "created_at"),
            ("patient_med_id", "created_at"),
            ("alert_type", "level"),
            ("dur_check_id",),
        ]
