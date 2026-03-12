from datetime import datetime, timedelta

import httpx
from fastapi import HTTPException
from starlette import status

from app.core import config
from app.dtos.documents import MfdsDrugItemResponse, MfdsDrugSearchResponse
from app.models.medications import DrugInfoCache


class MfdsService:
    # 식약처 약 정보 검색 - REQ-DRUG-001, REQ-DRUG-002
    async def search_easy_drug_info(self, drug_name: str, num_of_rows: int = 5) -> MfdsDrugSearchResponse:
        if not config.MFDS_SERVICE_KEY:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SERVICE_UNAVAILABLE")

        items = await self._request_easy_drug_info(drug_name=drug_name, num_of_rows=num_of_rows)
        await self._sync_drug_info_cache(items=items)

        response_items = [
            MfdsDrugItemResponse(
                item_seq=str(self._pick(item, "ITEM_SEQ", "itemSeq") or ""),
                item_name=str(self._pick(item, "ITEM_NAME", "itemName") or ""),
                entp_name=self._nullable_str(self._pick(item, "ENTP_NAME", "entpName")),
                efficacy=self._nullable_str(self._pick(item, "EE_DOC_DATA", "efcyQesitm")),
                dosage_info=self._nullable_str(self._pick(item, "UD_DOC_DATA", "useMethodQesitm")),
                precautions=self._nullable_str(self._pick(item, "NB_DOC_DATA", "atpnQesitm")),
            )
            for item in items
        ]

        return MfdsDrugSearchResponse(query=drug_name, total=len(response_items), items=response_items)

    # 식약처 e약은요 API 호출 - REQ-DRUG-001, REQ-DRUG-002
    async def _request_easy_drug_info(self, drug_name: str, num_of_rows: int) -> list[dict]:
        url = f"{config.MFDS_BASE_URL}/DrbEasyDrugInfoService/getDrbEasyDrugList"
        params = {
            "serviceKey": config.MFDS_SERVICE_KEY,
            "itemName": drug_name,
            "type": "json",
            "pageNo": 1,
            "numOfRows": num_of_rows,
        }

        timeout = httpx.Timeout(config.MFDS_TIMEOUT_SECONDS)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, params=params)

        if response.status_code >= status.HTTP_400_BAD_REQUEST:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SERVICE_UNAVAILABLE")

        payload = response.json()
        body = payload.get("body") or {}
        items = body.get("items") or []

        if isinstance(items, dict):
            return [items]
        if isinstance(items, list):
            return items
        return []

    # 식약처 조회결과 캐시 저장 - REQ-DRUG-003
    async def _sync_drug_info_cache(self, items: list[dict]) -> None:
        expires_at = datetime.now(config.TIMEZONE) + timedelta(days=7)
        for item in items:
            item_seq = self._nullable_str(self._pick(item, "ITEM_SEQ", "itemSeq"))
            if not item_seq:
                continue

            defaults = {
                "drug_name_display": self._nullable_str(self._pick(item, "ITEM_NAME", "itemName")),
                "manufacturer": self._nullable_str(self._pick(item, "ENTP_NAME", "entpName")),
                "efficacy": self._nullable_str(self._pick(item, "EE_DOC_DATA", "efcyQesitm")),
                "dosage_info": self._nullable_str(self._pick(item, "UD_DOC_DATA", "useMethodQesitm")),
                "precautions": self._nullable_str(self._pick(item, "NB_DOC_DATA", "atpnQesitm")),
                "storage_method": self._nullable_str(self._pick(item, "STORAGE_METHOD", "depositMethodQesitm")),
                "expires_at": expires_at,
            }

            existing_cache = await DrugInfoCache.get_or_none(mfds_item_seq=item_seq)
            if existing_cache:
                await DrugInfoCache.filter(id=existing_cache.id).update(**defaults)
                continue
            await DrugInfoCache.create(mfds_item_seq=item_seq, **defaults)

    @staticmethod
    def _nullable_str(value: object) -> str | None:
        if value is None:
            return None
        string_value = str(value).strip()
        return string_value or None

    @staticmethod
    def _pick(item: dict, *keys: str) -> object | None:
        for key in keys:
            if key in item and item.get(key) is not None:
                return item.get(key)
        return None
