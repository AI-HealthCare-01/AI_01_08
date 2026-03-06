from tortoise import fields, models


class Patient(models.Model):
    id = fields.BigIntField(primary_key=True)
    user = fields.OneToOneField("models.User", related_name="patient", null=True, on_delete=fields.SET_NULL)
    owner_user = fields.ForeignKeyField("models.User", related_name="owned_patients", on_delete=fields.CASCADE)
    display_name = fields.CharField(max_length=100, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "patients"

# 수정 건강프로필
class PatientProfile(models.Model):
    id = fields.BigIntField(pk=True)

    birth_year = fields.IntField(null=True)
    sex = fields.CharField(max_length=20, null=True)

    height_cm = fields.DecimalField(max_digits=6, decimal_places=2, null=True)
    weight_kg = fields.DecimalField(max_digits=6, decimal_places=2, null=True)
    bmi = fields.DecimalField(max_digits=6, decimal_places=2, null=True)

    conditions = fields.TextField(null=True)
    allergies = fields.TextField(null=True)
    notes = fields.TextField(null=True)

    # [각주] 복용약 리스트(list[str])를 DB에는 JSON 문자열로 저장하기 위한 컬럼
    meds_json = fields.TextField(null=True)

    # [각주] 생활습관/입원 관련(요구사항 확장 필드)
    is_smoker = fields.BooleanField(null=True)
    is_hospitalized = fields.BooleanField(null=True)
    discharge_date = fields.DateField(null=True)

    # [각주] 평균 습관 값(소수 1자리 반올림 전제로 저장)
    avg_sleep_hours_per_day = fields.DecimalField(max_digits=3, decimal_places=1, null=True)
    avg_cig_packs_per_week = fields.DecimalField(max_digits=4, decimal_places=1, null=True)
    avg_alcohol_bottles_per_week = fields.DecimalField(max_digits=4, decimal_places=1, null=True)

    # [각주] 운동은 분 단위 정수로 저장
    avg_exercise_minutes_per_day = fields.IntField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    patient = fields.OneToOneField("models.Patient", related_name="profile", on_delete=fields.CASCADE)

    class Meta:
        table = "patient_profiles"


class PatientProfileHistory(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="profile_histories", on_delete=fields.CASCADE)
    snapshot_json = fields.TextField()
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "patient_profile_history"


class InvitationCode(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.ForeignKeyField("models.Patient", related_name="invitation_codes", on_delete=fields.CASCADE)
    code = fields.CharField(max_length=100, unique=True)
    expires_at = fields.DatetimeField(null=True)
    used_at = fields.DatetimeField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "invitation_codes"


class CaregiverPatientLink(models.Model):
    id = fields.BigIntField(primary_key=True)
    caregiver_user = fields.ForeignKeyField("models.User", related_name="caregiver_links", on_delete=fields.CASCADE)
    patient = fields.ForeignKeyField("models.Patient", related_name="caregiver_links", on_delete=fields.CASCADE)
    status = fields.CharField(max_length=30)
    created_at = fields.DatetimeField(auto_now_add=True)
    revoked_at = fields.DatetimeField(null=True)

    class Meta:
        table = "caregiver_patient_links"
        unique_together = (("caregiver_user", "patient"),)
