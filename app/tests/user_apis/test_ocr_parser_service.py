from app.services.documents import DocumentService
from app.services.ocr import OcrService


def test_parse_extracted_meds_filters_receipt_noise():
    ocr_service = OcrService()
    raw_text = """
조제약사
백수정
약제비총액
약품사진
약품명
복약안내
뮤코스텐캡슐
백색 분말이 든 상단 암녹색 하단 담녹색 경질캡슐
완화시켜주는 약입니다.
코대원정
약품명
투약량
횟수
일수
총투
뮤코스텐캡슐
1
3
5
15
슈다페드정
1
3
5
15
코대원정
1
3
5
15
"""

    parsed_meds = ocr_service._parse_extracted_meds(raw_text=raw_text)
    parsed_names = [item["name"] for item in parsed_meds]

    assert "뮤코스텐캡슐" in parsed_names
    assert "슈다페드정" in parsed_names
    assert "코대원정" in parsed_names

    assert "백수정" not in parsed_names
    assert "약제비총액" not in parsed_names
    assert "경질캡슐" not in parsed_names
    assert "완화시켜주" not in parsed_names


def test_extract_barcode_values_from_raw_text():
    raw_text = """
[BARCODE_DETECTIONS]
type=QRCODE, value=https://example.com/qr/abc
type=CODE128, value=8801234567890
"""
    barcode_values = DocumentService._extract_barcode_values(raw_text=raw_text)
    assert barcode_values == ["https://example.com/qr/abc", "8801234567890"]


def test_parse_extracted_meds_uses_summary_schedule_map():
    ocr_service = OcrService()
    raw_text = """
복약안내
약품명
투약량
횟수
일수
총투
텔미누보정40/5m
1
1
60
60
코푸시럽
1
3
5
15
"""

    parsed_meds = ocr_service._parse_extracted_meds(raw_text=raw_text)
    parsed_map = {item["name"]: item for item in parsed_meds}

    assert "텔미누보정" in parsed_map
    assert parsed_map["텔미누보정"]["dosage_text"] == "1정씩"
    assert parsed_map["텔미누보정"]["frequency_text"] == "1회"
    assert parsed_map["텔미누보정"]["duration_text"] == "60일분"

    assert "코푸시럽" in parsed_map
    assert parsed_map["코푸시럽"]["dosage_text"] == "1포씩"
    assert parsed_map["코푸시럽"]["frequency_text"] == "3회"
    assert parsed_map["코푸시럽"]["duration_text"] == "5일분"


def test_parse_extracted_meds_excludes_receipt_rows_with_numeric_pattern():
    ocr_service = OcrService()
    raw_text = """
약품명
투약량
횟수
일수
총투
약제비총액
73980
뮤코스텐캡슐
1
3
5
15
"""

    parsed_meds = ocr_service._parse_extracted_meds(raw_text=raw_text)
    parsed_names = [item["name"] for item in parsed_meds]
    assert "뮤코스텐캡슐" in parsed_names
    assert "약제비총액" not in parsed_names
