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


class PatientProfile(models.Model):
    id = fields.BigIntField(primary_key=True)
    patient = fields.OneToOneField("models.Patient", related_name="profile", on_delete=fields.CASCADE)
    birth_year = fields.IntField(null=True)
    sex = fields.CharField(max_length=20, null=True)
    height_cm = fields.DecimalField(max_digits=6, decimal_places=2, null=True)
    weight_kg = fields.DecimalField(max_digits=6, decimal_places=2, null=True)
    bmi = fields.DecimalField(max_digits=6, decimal_places=2, null=True)
    conditions = fields.TextField(null=True)
    allergies = fields.TextField(null=True)
    notes = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

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
