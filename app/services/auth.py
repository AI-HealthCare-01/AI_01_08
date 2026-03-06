from fastapi.exceptions import HTTPException
from pydantic import EmailStr
from starlette import status
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.dtos.auth import LoginRequest, LoginRole, SignUpRequest
from app.models.healthcare import Role, UserRole
from app.models.users import User
from app.repositories.user_repository import UserRepository
from app.services.jwt import JwtService
from app.utils.common import normalize_phone_number
from app.utils.jwt.tokens import AccessToken, RefreshToken
from app.utils.security import hash_password, verify_password


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()
        self.jwt_service = JwtService()

    async def signup(self, data: SignUpRequest) -> User:
        # 이메일 중복 체크
        await self.check_email_exists(data.email)

        # 입력받은 휴대폰 번호를 노말라이즈
        normalized_phone_number = normalize_phone_number(data.phone_number)

        # 휴대폰 번호 중복 체크
        await self.check_phone_number_exists(normalized_phone_number)

        # 유저 생성
        async with in_transaction():
            user = await self.user_repo.create_user(
                email=data.email,
                hashed_password=hash_password(data.password),  # 해시화된 비밀번호를 사용
                name=data.name,
                phone_number=normalized_phone_number,
                gender=data.gender,
                birthday=data.birth_date,
            )
            default_role, _ = await Role.get_or_create(
                code=LoginRole.PATIENT.value, defaults={"name": LoginRole.PATIENT.value}
            )
            await UserRole.get_or_create(user=user, role=default_role)

            return user

    async def authenticate(self, data: LoginRequest) -> User:
        # 이메일로 사용자 조회
        email = str(data.email)
        user = await self.user_repo.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # 비밀번호 검증
        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="이메일 또는 비밀번호가 올바르지 않습니다."
            )

        # 활성 사용자 체크
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="비활성화된 계정입니다.")

        return user

    async def login(self, user: User, *, role: LoginRole) -> dict[str, AccessToken | RefreshToken]:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="비활성화된 계정입니다.")
        role_name = self._normalize_role_name(role)
        role_assigned = (
            await UserRole.filter(user_id=user.id).filter(Q(role__name=role_name) | Q(role__code=role_name)).exists()
        )
        if not role_assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="선택한 역할로 로그인할 수 없습니다.")
        return self.jwt_service.issue_jwt_pair(user, extra_claims={"login_role": role_name})

    async def check_email_exists(self, email: str | EmailStr) -> None:
        if await self.user_repo.exists_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 이메일입니다.")

    async def check_phone_number_exists(self, phone_number: str) -> None:
        if await self.user_repo.exists_by_phone_number(phone_number):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 사용중인 휴대폰 번호입니다.")

    @staticmethod
    def _normalize_role_name(role: LoginRole) -> str:
        if role in (LoginRole.GUARDIAN, LoginRole.CAREGIVER):
            return LoginRole.CAREGIVER.value
        return LoginRole.PATIENT.value
