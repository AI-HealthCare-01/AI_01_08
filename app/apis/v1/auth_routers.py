from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse as Response

from app.core import config
from app.core.config import Env
from app.dtos.auth import (
    LoginRequest,
    LoginResponse,
    LoginRole,
    SignUpRequest,
    SocialLoginStartResponse,
    SocialProvider,
    TokenRefreshResponse,
)
from app.services.auth import AuthService
from app.services.jwt import JwtService
from app.services.social_auth import SocialAuthService

auth_router = APIRouter(prefix="/auth", tags=["auth"])


def _build_login_response(tokens: dict, login_role: LoginRole) -> Response:
    resp = Response(
        content=LoginResponse(access_token=str(tokens["access_token"]), login_role=login_role).model_dump(),
        status_code=status.HTTP_200_OK,
    )
    resp.set_cookie(
        key="refresh_token",
        value=str(tokens["refresh_token"]),
        httponly=True,
        secure=True if config.ENV == Env.PROD else False,
        domain=config.COOKIE_DOMAIN or None,
        expires=tokens["access_token"].payload["exp"],
    )
    return resp


@auth_router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignUpRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    await auth_service.signup(request)
    return Response(content={"detail": "회원가입이 성공적으로 완료되었습니다."}, status_code=status.HTTP_201_CREATED)


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(
    request: LoginRequest,
    auth_service: Annotated[AuthService, Depends(AuthService)],
) -> Response:
    user = await auth_service.authenticate(request)
    tokens = await auth_service.login(user, role=request.role)
    return _build_login_response(tokens, login_role=request.role)


@auth_router.get(
    "/social/{provider}/login",
    response_model=SocialLoginStartResponse,
    status_code=status.HTTP_200_OK,
)
async def social_login_start(
    provider: SocialProvider,
    social_auth_service: Annotated[SocialAuthService, Depends(SocialAuthService)],
    role: Annotated[LoginRole, Query()] = LoginRole.PATIENT,
) -> SocialLoginStartResponse:
    authorize_url = social_auth_service.build_authorize_url(provider=provider, role=role)
    return SocialLoginStartResponse(provider=provider, authorize_url=authorize_url)


@auth_router.get("/social/{provider}/callback", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def social_login_callback(
    provider: SocialProvider,
    code: Annotated[str, Query(min_length=1)],
    social_auth_service: Annotated[SocialAuthService, Depends(SocialAuthService)],
    auth_service: Annotated[AuthService, Depends(AuthService)],
    state: Annotated[str | None, Query()] = None,
    role: Annotated[LoginRole | None, Query()] = None,
) -> Response:
    profile = await social_auth_service.exchange_code_and_fetch_profile(provider=provider, code=code, state=state)
    provider_user_id = profile.get("provider_user_id")
    if not provider_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provider user id is missing.")
    user = await social_auth_service.get_or_create_user_by_social(
        provider=provider,
        provider_user_id=provider_user_id,
        email=profile.get("email"),
        name=profile.get("name") or f"{provider.value}-user",
    )
    selected_role = social_auth_service.resolve_role(requested_role=role, state=state)
    tokens = await auth_service.login(user, role=selected_role)
    return _build_login_response(tokens, login_role=selected_role)


@auth_router.get("/token/refresh", response_model=TokenRefreshResponse, status_code=status.HTTP_200_OK)
async def token_refresh(
    jwt_service: Annotated[JwtService, Depends(JwtService)],
    refresh_token: Annotated[str | None, Cookie()] = None,
) -> Response:
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing.")
    access_token = jwt_service.refresh_jwt(refresh_token)
    return Response(
        content=TokenRefreshResponse(access_token=str(access_token)).model_dump(), status_code=status.HTTP_200_OK
    )
