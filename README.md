# CareBridge | 진료 기록 기반 복약 안내 및 생활습관 가이드 시스템

진료 기록(문서 OCR) 기반으로 복약 안내와 생활습관 가이드를 자동 생성하는 헬스케어 서비스입니다.

## 서비스 화면
![케어브릿지 메인 화면](docs/images/carebridge-main.png)

## 팀 정보
- 팀명: (주)케어브릿지
- 구성원: 김혜민, 김민지, 김태은, 홍영주
- 서비스 도메인: https://care-bridge.site/

## 프로젝트 주제
- 진료 기록 기반 복약 안내 및 생활습관 개선 가이드 자동 생성 시스템
- 의료 기록 데이터를 기반으로 OCR + OpenAPI + LLM + 비동기 워커를 결합해 환자/보호자 지원 기능을 제공합니다.

## 핵심 기능
- 이메일/소셜(카카오) 로그인 및 역할 기반 접근 제어(PATIENT, CAREGIVER, ADMIN)
- 문서 업로드/목록/삭제, OCR 비동기 처리, 추출 약물 수정/확정
- MFDS 약 정보 조회 및 캐시 저장
- AI 복약 가이드 생성/재생성(비동기), 보호자 요약 생성
- 환자-보호자 초대코드 연동
- 챗봇 세션/메시지/피드백 저장 및 비동기 응답 생성
- 복약 체크/이행률/알림/병원 일정/관리자 대시보드

## 아키텍처
- `nginx`가 `/api/*` 요청을 `fastapi`로 프록시하고 `/app/*` 정적 프론트를 서빙
- `fastapi`는 API/비즈니스 로직 처리, MySQL(Tortoise ORM) 저장
- `ai-worker`는 `ai_tasks`, `chat_tasks` 큐를 소비해 가이드/챗봇 응답 생성
- `app-worker`는 `notification_queue` 큐를 소비해 알림 발송 처리
- `redis`는 작업 큐 브로커, `mysql`은 영속 저장소

## 기술 스택

| 영역 | 스택 |
|---|---|
| Backend | FastAPI, Uvicorn, Tortoise ORM, Pydantic v2 |
| Worker/Queue | Redis, 비동기 Worker(`ai_worker`, `app_worker`) |
| AI/외부 연동 | OpenAI Chat Completions, MFDS OpenAPI, Naver OCR, KIDS |
| Database | MySQL 8 |
| Frontend | React 18, Vite 5, Bootstrap 5 |
| Infra | Docker Compose, Nginx, Certbot |
| Tooling | uv, Ruff, MyPy, Pytest, GitHub Actions(CI lint) |

## 로컬 실행

### 1) 환경 변수 준비
```bash
cp envs/example.local.env envs/.local.env
ln -sf envs/.local.env .env
```

### 2) 전체 스택 실행
```bash
docker compose up -d --build
```

### 3) 접속 경로
- 서비스(운영): `https://care-bridge.site/`
- API 문서: `http://localhost/api/docs`
- OpenAPI JSON: `http://localhost/api/openapi.json`
- 프로젝트 문서(MkDocs): `http://localhost/api/project-docs/`
- 프론트(개발 서버): `http://localhost:5173`

## 배포 방식

현재 브랜치는 GitHub Actions에서 배포 자동화(CD)는 없고, 아래 수동 흐름입니다.

1. 이미지 빌드/푸시  
`docker-compose.build.yml` 기반으로 `fastapi`, `ai-worker`, `nginx` 이미지를 태깅/푸시

2. 서버 배포  
EC2에서 `docker-compose.prod.yml`로 이미지 pull 후 기동

3. 트래픽 처리  
Nginx가 80/443을 수신하고 API/정적 리소스를 라우팅, Certbot 컨테이너가 인증서 갱신 담당

상세 명령은 `docs/deployment.md`를 참고하세요.

## 문서
- API 명세: `docs/api-spec.md`
- 배포/운영 가이드: `docs/deployment.md`
- 요구사항 추적표: `docs/requirements-traceability.md`
- 문서 홈: `docs/index.md`

## 개발 검증 명령
```bash
uv sync --frozen
uv run ruff check .
uv run ruff format . --check
```
