# app/dtos/medication_intake_dtos.py
from __future__ import annotations
from datetime import date, datetime, time
from typing import List, Optional, Literal
from pydantic import BaseModel

IntakeStatus = Literal["taken", "missed", "pending", "skipped"]

class IntakeItem(BaseModel):
    schedule_id: int
    schedule_time_id: int
    patient_med_id: int
    scheduled_at: datetime
    status: IntakeStatus
    taken_at: Optional[datetime] = None
    note: Optional[str] = None

class DailyIntakeStatus(BaseModel):
    day: date
    items: List[IntakeItem]

class AdherenceSummary(BaseModel):
    expected_total: int
    taken: int
    missed: int
    pending: int
    skipped: int
    overall_rate: float          # taken / expected_total
    completed_rate: Optional[float] = None  # taken / (taken + missed + skipped)

class IntakeStatusResponse(BaseModel):
    patient_id: int
    date_from: date
    date_to: date
    days: List[DailyIntakeStatus]
    summary: AdherenceSummary