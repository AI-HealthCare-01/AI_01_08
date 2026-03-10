from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BarcodeDetection:
    barcode_type: str
    barcode_value: str


class BarcodeService:
    # REQ-DOC-009 - 바코드 인식
    def extract_from_file(self, file_path: Path) -> list[BarcodeDetection]:
        suffix = file_path.suffix.lower()
        detections: list[BarcodeDetection] = []

        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}:
            detections.extend(self._decode_image_with_zxing(file_path=file_path))
            detections.extend(self._decode_image_with_pyzbar(file_path=file_path))
            detections.extend(self._decode_image_with_qr_detector(file_path=file_path))
            return self._deduplicate(detections)

        if suffix == ".pdf":
            detections.extend(self._decode_pdf_with_zxing(file_path=file_path))
            detections.extend(self._decode_pdf_with_pyzbar(file_path=file_path))
            return self._deduplicate(detections)

        return []

    # REQ-DOC-009 - 이미지 바코드 디코딩(zxing-cpp)
    @staticmethod
    def _decode_image_with_zxing(file_path: Path) -> list[BarcodeDetection]:
        try:
            import zxingcpp
            from PIL import Image
        except ImportError:
            return []

        try:
            with Image.open(file_path) as image:
                results = zxingcpp.read_barcodes(image)
        except Exception:  # noqa: BLE001
            return []

        detections: list[BarcodeDetection] = []
        for result in results:
            raw_value = str(getattr(result, "text", "")).strip()
            if not raw_value:
                continue
            barcode_type = str(getattr(result, "format", "UNKNOWN")).replace("BarcodeFormat.", "").upper()
            detections.append(
                BarcodeDetection(
                    barcode_type=barcode_type,
                    barcode_value=raw_value,
                )
            )
        return detections

    # REQ-DOC-009 - 이미지 바코드 디코딩(pyzbar)
    @staticmethod
    def _decode_image_with_pyzbar(file_path: Path) -> list[BarcodeDetection]:
        try:
            from PIL import Image
            from pyzbar.pyzbar import decode as zbar_decode
        except ImportError:
            return []

        try:
            with Image.open(file_path) as image:
                decoded_objects = zbar_decode(image)
        except Exception:  # noqa: BLE001
            return []

        detections: list[BarcodeDetection] = []
        for obj in decoded_objects:
            raw_value = obj.data.decode("utf-8", errors="ignore").strip()
            if not raw_value:
                continue
            detections.append(
                BarcodeDetection(
                    barcode_type=str(obj.type).upper(),
                    barcode_value=raw_value,
                )
            )
        return detections

    # REQ-DOC-009 - 이미지 바코드 디코딩(OpenCV QR fallback)
    @staticmethod
    def _decode_image_with_qr_detector(file_path: Path) -> list[BarcodeDetection]:
        try:
            import cv2
        except ImportError:
            return []

        image = cv2.imread(str(file_path))
        if image is None:
            return []

        detector = cv2.QRCodeDetector()
        value, _, _ = detector.detectAndDecode(image)
        if not value:
            return []
        return [BarcodeDetection(barcode_type="QRCODE", barcode_value=value.strip())]

    # REQ-DOC-009 - PDF 바코드 디코딩(zxing-cpp)
    @staticmethod
    def _decode_pdf_with_zxing(file_path: Path) -> list[BarcodeDetection]:
        try:
            import zxingcpp
            from pdf2image import convert_from_path
        except ImportError:
            return []

        try:
            pages = convert_from_path(str(file_path), dpi=220, first_page=1, last_page=2)
        except Exception:  # noqa: BLE001
            return []

        detections: list[BarcodeDetection] = []
        for page in pages:
            try:
                results = zxingcpp.read_barcodes(page)
            except Exception:  # noqa: BLE001
                continue
            for result in results:
                raw_value = str(getattr(result, "text", "")).strip()
                if not raw_value:
                    continue
                barcode_type = str(getattr(result, "format", "UNKNOWN")).replace("BarcodeFormat.", "").upper()
                detections.append(
                    BarcodeDetection(
                        barcode_type=barcode_type,
                        barcode_value=raw_value,
                    )
                )
        return detections

    # REQ-DOC-009 - PDF 바코드 디코딩(선택)
    @staticmethod
    def _decode_pdf_with_pyzbar(file_path: Path) -> list[BarcodeDetection]:
        try:
            from pdf2image import convert_from_path
            from pyzbar.pyzbar import decode as zbar_decode
        except ImportError:
            return []

        try:
            pages = convert_from_path(str(file_path), dpi=220, first_page=1, last_page=2)
        except Exception:  # noqa: BLE001
            return []

        detections: list[BarcodeDetection] = []
        for page in pages:
            try:
                decoded_objects = zbar_decode(page)
            except Exception:  # noqa: BLE001
                continue
            for obj in decoded_objects:
                raw_value = obj.data.decode("utf-8", errors="ignore").strip()
                if not raw_value:
                    continue
                detections.append(
                    BarcodeDetection(
                        barcode_type=str(obj.type).upper(),
                        barcode_value=raw_value,
                    )
                )
        return detections

    @staticmethod
    def _deduplicate(detections: list[BarcodeDetection]) -> list[BarcodeDetection]:
        deduplicated: list[BarcodeDetection] = []
        seen: set[tuple[str, str]] = set()
        for detection in detections:
            key = (detection.barcode_type, detection.barcode_value)
            if key in seen:
                continue
            seen.add(key)
            deduplicated.append(detection)
        return deduplicated
