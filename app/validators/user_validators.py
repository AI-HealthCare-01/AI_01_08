import re
from datetime import date, datetime

from app.core import config


def validate_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다.")

    if not re.search(r"[A-Z]", password):
        raise ValueError("비밀번호는 대문자, 소문자, 숫자, 특수문자를 각각 1개 이상 포함해야 합니다.")

    if not re.search(r"[a-z]", password):
        raise ValueError("비밀번호는 대문자, 소문자, 숫자, 특수문자를 각각 1개 이상 포함해야 합니다.")

    if not re.search(r"[0-9]", password):
        raise ValueError("비밀번호는 대문자, 소문자, 숫자, 특수문자를 각각 1개 이상 포함해야 합니다.")

    if not re.search(r"[^a-zA-Z0-9]", password):
        raise ValueError("비밀번호는 대문자, 소문자, 숫자, 특수문자를 각각 1개 이상 포함해야 합니다.")

    return password


def validate_phone_number(phone_number: str) -> str:
    patterns = [
        r"010-\d{4}-\d{4}",
        r"010\d{8}",
        r"\+8210\d{8}",
    ]

    if not any(re.fullmatch(p, phone_number) for p in patterns):
        raise ValueError("유효하지 않은 전화번호 형식입니다.")

    return phone_number


def validate_birthday(birthday: date | str) -> date:
    if isinstance(birthday, str):
        try:
            birthday = date.fromisoformat(birthday)
        except ValueError as e:
            raise ValueError("올바르지 않은 날짜 형식입니다. format: YYYY-MM-DD") from e

    today = datetime.now(tz=config.TIMEZONE).date()
    if birthday > today:
        raise ValueError("생년월일은 오늘 날짜보다 클 수 없습니다.")

    return birthday
