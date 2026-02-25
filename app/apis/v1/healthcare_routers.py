from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from tortoise import models

from app.models import healthcare
from app.models.users import User

healthcare_router = APIRouter(prefix="/healthcare", tags=["healthcare"])


def _register_crud(
    parent_router: APIRouter,
    model: type[models.Model],
    path: str,
) -> None:
    router = APIRouter(prefix=f"/{path}", tags=[f"healthcare:{path}"])

    async def _row_or_none(item_id: int) -> dict[str, Any] | None:
        rows = await model.filter(id=item_id).values()
        return rows[0] if rows else None

    @router.post(
        "",
        status_code=status.HTTP_201_CREATED,
    )
    async def create_item(payload: dict[str, Any]):
        item = await model.create(**payload)
        return await _row_or_none(item.id)

    @router.get("")
    async def list_items(
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
    ):
        return await model.all().offset(offset).limit(limit).values()

    @router.get("/{item_id}")
    async def get_item(item_id: int):
        item = await _row_or_none(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path} not found")
        return item

    @router.put("/{item_id}")
    async def update_item(item_id: int, payload: dict[str, Any]):
        item = await model.get_or_none(id=item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path} not found")
        for key, value in payload.items():
            setattr(item, key, value)
        await item.save()
        return await _row_or_none(item_id)

    @router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_item(item_id: int):
        deleted = await model.filter(id=item_id).delete()
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path} not found")
        return None

    parent_router.include_router(router)


MODEL_REGISTRY: list[tuple[type[models.Model], str]] = [
    (healthcare.CodeGroup, "code-groups"),
    (healthcare.Code, "codes"),
    (healthcare.PhoneVerification, "phone-verifications"),
    (healthcare.AuthAccount, "auth-accounts"),
    (healthcare.RefreshToken, "refresh-tokens"),
    (healthcare.Role, "roles"),
    (healthcare.UserRole, "user-roles"),
    (healthcare.Patient, "patients"),
    (healthcare.PatientProfile, "patient-profiles"),
    (healthcare.PatientProfileHistory, "patient-profile-history"),
    (healthcare.InvitationCode, "invitation-codes"),
    (healthcare.CaregiverPatientLink, "caregiver-patient-links"),
    (healthcare.Document, "documents"),
    (healthcare.OcrJob, "ocr-jobs"),
    (healthcare.OcrRawText, "ocr-raw-texts"),
    (healthcare.ExtractedMed, "extracted-meds"),
    (healthcare.DrugCatalog, "drug-catalog"),
    (healthcare.DrugInfoCache, "drug-info-cache"),
    (healthcare.PatientMed, "patient-meds"),
    (healthcare.MedSchedule, "med-schedules"),
    (healthcare.MedScheduleTime, "med-schedule-times"),
    (healthcare.IntakeLog, "intake-logs"),
    (healthcare.Reminder, "reminders"),
    (healthcare.UserDevice, "user-devices"),
    (healthcare.Notification, "notifications"),
    (healthcare.Guide, "guides"),
    (healthcare.GuideSummary, "guide-summaries"),
    (healthcare.GuideFeedback, "guide-feedback"),
    (healthcare.ChatSession, "chat-sessions"),
    (healthcare.ChatMessage, "chat-messages"),
    (healthcare.DurCheck, "dur-checks"),
    (healthcare.DurAlert, "dur-alerts"),
]

for m, p in MODEL_REGISTRY:
    _register_crud(healthcare_router, m, p)


@healthcare_router.get("/summary")
async def healthcare_summary():
    table_counts = {}
    for model, path in MODEL_REGISTRY:
        table_counts[path] = await model.all().count()

    recent_patients = await healthcare.Patient.all().order_by("-id").limit(10).values(
        "id",
        "display_name",
        "owner_user_id",
        "created_at",
    )
    recent_users_raw = await User.all().order_by("-id").limit(10).values(
        "id",
        "email",
        "name",
        "phone_number",
        "created_at",
    )
    recent_users = [
        {
            "id": row["id"],
            "email": row["email"],
            "name": row["name"],
            "phone": row["phone_number"],
            "created_at": row["created_at"],
        }
        for row in recent_users_raw
    ]

    return {
        "table_counts": table_counts,
        "recent_patients": recent_patients,
        "recent_users": recent_users,
    }
