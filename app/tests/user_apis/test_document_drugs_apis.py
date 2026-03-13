from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.documents import Document, ExtractedMed, OcrJob
from app.models.healthcare import Role, UserRole
from app.models.medications import PatientMed
from app.models.patients import Patient
from app.models.users import User


class TestDocumentDrugsApis(TestCase):
    async def test_get_document_drugs_success(self):
        signup_data = {
            "email": "patient.docs1@gmail.com",
            "password": "Password123!",
            "name": "문서환자1",
            "gender": "FEMALE",
            "birth_date": "1993-03-03",
            "phone_number": "01070001111",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=signup_data)

            user = await User.get(email=signup_data["email"])
            patient_role, _ = await Role.get_or_create(code="PATIENT", defaults={"name": "PATIENT"})
            await UserRole.get_or_create(user_id=user.id, role_id=patient_role.id)
            patient = await Patient.create(user_id=user.id, owner_user_id=user.id, display_name="문서환자1")

            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": signup_data["email"], "password": signup_data["password"]},
            )
            access_token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            document = await Document.create(
                patient_id=patient.id,
                uploaded_by_user_id=user.id,
                file_url="uploads/documents/test.jpg",
                original_filename="test.jpg",
                file_type="image",
                status="uploaded",
            )
            ocr_job = await OcrJob.create(document_id=document.id, patient_id=patient.id, status="success")
            await ExtractedMed.create(
                ocr_job_id=ocr_job.id,
                patient_id=patient.id,
                name="암로디핀정",
                dosage_text="5mg",
                frequency_text="하루 1회",
                duration_text="30일",
                confidence=0.9,
            )

            response = await client.get(f"/api/v1/documents/{document.id}/drugs", headers=headers)
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data["document_id"] == document.id
            assert data["total"] == 1
            assert data["items"][0]["name"] == "암로디핀정"
            assert data["items"][0]["dosage_text"] == "5mg"

    async def test_patch_document_drugs_confirm_success(self):
        signup_data = {
            "email": "patient.docs2@gmail.com",
            "password": "Password123!",
            "name": "문서환자2",
            "gender": "MALE",
            "birth_date": "1992-04-04",
            "phone_number": "01070002222",
        }

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=signup_data)

            user = await User.get(email=signup_data["email"])
            patient_role, _ = await Role.get_or_create(code="PATIENT", defaults={"name": "PATIENT"})
            await UserRole.get_or_create(user_id=user.id, role_id=patient_role.id)
            patient = await Patient.create(user_id=user.id, owner_user_id=user.id, display_name="문서환자2")

            login_response = await client.post(
                "/api/v1/auth/login",
                json={"email": signup_data["email"], "password": signup_data["password"]},
            )
            access_token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}

            document = await Document.create(
                patient_id=patient.id,
                uploaded_by_user_id=user.id,
                file_url="uploads/documents/test2.jpg",
                original_filename="test2.jpg",
                file_type="image",
                status="uploaded",
            )
            ocr_job = await OcrJob.create(document_id=document.id, patient_id=patient.id, status="success")
            extracted_med = await ExtractedMed.create(
                ocr_job_id=ocr_job.id,
                patient_id=patient.id,
                name="타이레놀정",
                dosage_text="500mg",
                confidence=0.8,
            )

            patch_payload = {
                "items": [
                    {
                        "extracted_med_id": extracted_med.id,
                        "name": "타이레놀정",
                        "dosage_text": "650mg",
                        "frequency_text": "필요 시",
                        "duration_text": "7일",
                        "confidence": 0.95,
                    },
                    {
                        "name": "암로디핀정",
                        "dosage_text": "5mg",
                        "frequency_text": "하루 1회",
                        "duration_text": "30일",
                        "confidence": 0.91,
                    },
                ],
                "replace_all": False,
                "confirm": True,
                "force_confirm": True,
            }

            response = await client.patch(f"/api/v1/documents/{document.id}/drugs", json=patch_payload, headers=headers)
            assert response.status_code == status.HTTP_200_OK

            data = response.json()
            assert data["document_id"] == document.id
            assert data["updated_count"] == 2
            assert data["confirmed"] is True
            assert data["confirmed_patient_med_count"] == 2

            await extracted_med.refresh_from_db()
            assert extracted_med.dosage_text == "650mg"
            assert extracted_med.frequency_text == "필요 시"

            active_patient_meds = await PatientMed.filter(
                patient_id=patient.id,
                source_document_id=document.id,
                is_active=True,
            )
            assert len(active_patient_meds) == 2
