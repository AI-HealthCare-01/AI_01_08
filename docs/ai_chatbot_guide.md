# AI 챗봇 기능 사용 가이드

## 개요
OpenAI API를 사용하여 복약 관리 및 건강 상담을 제공하는 AI 챗봇 기능이 추가되었습니다.

## 설정

### 1. 환경 변수 설정
`envs/.local.env` 파일에 다음 환경 변수를 추가하세요:

```env
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini
```

### 2. 서버 재시작
환경 변수를 추가한 후 서버를 재시작하세요:

```bash
# Docker Compose 사용 시
docker-compose down
docker-compose up -d --build

# 로컬 개발 시
uv run uvicorn app.main:app --reload
```

## 사용 방법

### 1. 웹 인터페이스
1. 로그인 후 대시보드에서 "AI 상담" 버튼 클릭
2. AI 가이드 페이지 하단의 챗봇 섹션에서 메시지 입력
3. "약속이"가 복약 관리 및 건강 관련 질문에 답변

### 2. API 엔드포인트

**POST** `/api/v1/ai-chat`

**요청 본문:**
```json
{
  "message": "고혈압 약을 언제 먹어야 하나요?",
  "patient_context": "이름: 홍길동, 역할: PATIENT"
}
```

**응답:**
```json
{
  "response": "고혈압 약은 일반적으로 아침 식사 후 30분 이내에 복용하는 것이 좋습니다..."
}
```

**인증:** Bearer Token 필요

## 기능

- 복약 관련 질문 답변
- 생활습관 개선 조언
- 건강 관리 정보 제공
- 환자 맥락 기반 맞춤형 답변

## 주의사항

- OpenAI API 키가 설정되지 않으면 500 에러 발생
- API 호출 시 타임아웃은 30초로 설정
- 응답 최대 토큰 수: 1000
- Temperature: 0.7 (창의적이면서도 일관된 답변)

## 문제 해결

### API 키 오류
```
OpenAI API 키가 설정되지 않았습니다.
```
→ `.env` 파일에 `OPENAI_API_KEY` 추가 후 서버 재시작

### 타임아웃 오류
```
AI 응답 시간 초과
```
→ 네트워크 연결 확인 또는 타임아웃 시간 증가

### 권한 오류
```
401 Unauthorized
```
→ 로그인 후 유효한 액세스 토큰으로 요청
