# 배포/운영 가이드

## 현재 배포 방식 요약
- 배포 자동화(CD) 워크플로우는 없습니다.
- `.github/workflows/checks.yml`은 lint 중심 CI만 수행합니다.
- 운영 배포는 Docker 이미지 수동 빌드/푸시 후, 서버에서 `docker-compose.prod.yml`로 기동합니다.

## 구성 파일
- 이미지 빌드: `docker-compose.build.yml`
- 운영 기동: `docker-compose.prod.yml`
- 개발/로컬: `docker-compose.yml`
- 리버스 프록시: `nginx/default.conf` (필요 시 `nginx/prod_http.conf`, `nginx/prod_https.conf` 참고)
- 환경 변수 예시: `envs/example.prod.env`

## 운영 아키텍처
- `nginx`: 80/443 수신, `/api/*`를 `fastapi`로 프록시, `/app/*` 정적 파일 제공
- `fastapi`: API 서버
- `ai-worker`: 가이드/챗봇 비동기 처리 (`ai_tasks`, `chat_tasks`)
- `app-worker`: 알림 비동기 처리 (`notification_queue`)
- `redis`: 큐 브로커
- `mysql`: 데이터 저장소
- `certbot`: 인증서 갱신

## 1) 이미지 빌드/푸시

### 사전 준비
```bash
cp envs/example.prod.env envs/.prod.env
ln -sf envs/.prod.env .env
```

`envs/.prod.env`에서 아래 값을 반드시 채웁니다.
- `DOCKER_USER`
- `DOCKER_REPOSITORY`
- `APP_VERSION`
- `AI_WORKER_VERSION`
- `OPENAI_API_KEY`
- `MFDS_SERVICE_KEY`
- `NAVER_OCR_API_URL`, `NAVER_OCR_SECRET_KEY`

### 단일 플랫폼 빌드/푸시
```bash
docker login
docker compose -f docker-compose.build.yml --env-file envs/.prod.env build
docker compose -f docker-compose.build.yml --env-file envs/.prod.env push
```

### 멀티 아키텍처(amd64/arm64) 빌드/푸시
```bash
docker buildx bake --file docker-compose.build.yml --push
```

## 2) 서버 배포(EC2)
```bash
git pull origin <branch>
ln -sf envs/.prod.env .env
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

검증:
```bash
docker compose -f docker-compose.prod.yml ps
curl -f http://<SERVER_OR_DOMAIN>/api/health
```

## 3) HTTPS 운영
- `docker-compose.prod.yml`는 Certbot 볼륨(`certbot-conf`, `certbot-www`)을 포함합니다.
- HTTPS 설정 시 `nginx/default.conf`가 SSL 경로를 참조하도록 구성되어야 합니다.
- 팀 운영 정책에 따라 `nginx/prod_https.conf`를 `nginx/default.conf`에 반영해 배포합니다.

## 운영 점검 명령
```bash
docker compose -f docker-compose.prod.yml logs -f fastapi
docker compose -f docker-compose.prod.yml logs -f ai-worker
docker compose -f docker-compose.prod.yml logs -f app-worker
docker compose -f docker-compose.prod.yml logs -f nginx
```

## 롤백
- 이미지 태그(`APP_VERSION`, `AI_WORKER_VERSION`)를 이전 버전으로 변경 후 `up -d` 재실행합니다.

```bash
docker compose -f docker-compose.prod.yml up -d
```

## 보안 주의사항
- 현재 `docker-compose.prod.yml`은 MySQL/Redis 포트 매핑을 포함합니다.
- 운영에서는 Security Group/방화벽으로 외부 접근을 제한해야 합니다.
- 목표 정책은 `80/443/22` 외 포트 비공개입니다.
