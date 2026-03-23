# API 명세

## 기본 정보
- Base URL: `http(s)://<host>`
- Swagger UI: `/api/docs`
- OpenAPI JSON: `/api/openapi.json`
- API Prefix: `/api/v1`
- Health Check: `GET /api/health`

## 인증 방식
- 로그인 성공 시 `access_token`은 응답 바디로 반환
- `refresh_token`은 HttpOnly Cookie로 저장
- 인증이 필요한 API는 `Authorization: Bearer <access_token>` 헤더 사용

```http
Authorization: Bearer eyJhbGciOi...
```

## 응답 규약
- 라우터별로 응답 형식이 혼재합니다.
- `auth/user/document/guide/chat` 계열은 일반 JSON 응답이 많습니다.
- `notifications/patient_profile` 계열은 `{"success": true, "data": ...}` envelope를 사용합니다.
- 최종 스키마는 Swagger(`/api/docs`)를 기준으로 확인합니다.

## 인증/권한

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/auth/signup` | 이메일 회원가입 |
| POST | `/api/v1/auth/login` | 이메일 로그인 |
| POST | `/api/v1/auth/logout` | 로그아웃(쿠키 삭제) |
| GET | `/api/v1/auth/token/refresh` | Refresh 기반 Access 재발급 |
| GET | `/api/v1/auth/social/kakao/login` | 카카오 로그인 시작 URL 발급 |
| GET | `/api/v1/auth/social/kakao/callback` | 카카오 로그인 콜백 |
| POST | `/api/v1/auth/find-email` | 이메일 찾기 |
| POST | `/api/v1/auth/reset-password` | 비밀번호 재설정 |
| POST | `/api/v1/auth/admin/login` | 관리자 로그인 |
| POST | `/api/v1/auth/admin/signup` | 관리자 가입 |
| GET | `/api/v1/auth/admin/signup` | 관리자 가입 페이지(HTML) |
| GET | `/api/v1/public/roles` | 역할 목록 조회 |

## 사용자/연동/설정

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/users/me` | 내 정보 조회 |
| PATCH | `/api/v1/users/me` | 내 정보 수정 |
| DELETE | `/api/v1/users/me` | 회원 탈퇴(비활성화) |
| POST | `/api/v1/users/me/devices/register` | 디바이스 등록 |
| POST | `/api/v1/users/invite-code` | 초대코드 생성 |
| DELETE | `/api/v1/users/invite-code` | 초대코드 폐기 |
| POST | `/api/v1/users/link` | 초대코드로 보호자 연동 |
| GET | `/api/v1/users/links` | 연동 목록 조회 |
| DELETE | `/api/v1/users/links/{link_id}` | 연동 해제 |
| GET | `/api/v1/users/me/health-profile` | 내 건강 프로필 조회 |
| POST | `/api/v1/users/me/health-profile` | 내 건강 프로필 생성 |
| PATCH | `/api/v1/users/me/health-profile` | 내 건강 프로필 수정 |
| DELETE | `/api/v1/users/me/health-profile` | 내 건강 프로필 삭제 |
| GET | `/api/v1/users/links/{link_id}/health-profile` | 연동 환자 프로필 조회 |
| POST | `/api/v1/users/links/{link_id}/health-profile` | 연동 환자 프로필 생성 |
| PATCH | `/api/v1/users/links/{link_id}/health-profile` | 연동 환자 프로필 수정 |
| DELETE | `/api/v1/users/links/{link_id}/health-profile` | 연동 환자 프로필 삭제 |
| GET | `/api/v1/settings` | 사용자 설정 조회 |
| PATCH | `/api/v1/settings` | 사용자 설정 수정 |

## 문서/OCR/약물

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/documents/upload` | 문서 업로드 + OCR 작업 생성 |
| GET | `/api/v1/documents` | 문서 목록/필터 조회 |
| DELETE | `/api/v1/documents/{document_id}` | 문서 soft delete |
| PATCH | `/api/v1/documents/{document_id}/title` | 문서명 변경 |
| GET | `/api/v1/documents/{document_id}/file` | 원본 파일 다운로드 |
| GET | `/api/v1/documents/{document_id}/drugs` | 추출 약물 조회 |
| PATCH | `/api/v1/documents/{document_id}/drugs` | 추출 약물 수정/확정 |
| GET | `/api/v1/documents/medication-guide` | 환자 복약안내 카드 조회 |
| GET | `/api/v1/documents/{document_id}/status` | OCR 상태 조회 |
| GET | `/api/v1/documents/{document_id}/ocr-text` | OCR 원문 조회 |
| POST | `/api/v1/documents/{document_id}/retry` | OCR 재시도 |
| POST | `/api/v1/documents/barcodes/decode` | 바코드 디코드 |
| GET | `/api/v1/documents/mfds/search` | MFDS 약 검색 |

## 가이드/챗봇

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/v1/guides/generate` | 가이드 생성 요청(비동기) |
| GET | `/api/v1/guides` | 가이드 목록 조회 |
| GET | `/api/v1/guides/{guide_id}` | 가이드 상세 조회 |
| POST | `/api/v1/guides/{guide_id}/regenerate` | 가이드 재생성 |
| POST | `/api/v1/chat/sessions` | 채팅 세션 생성 |
| POST | `/api/v1/chat/sessions/{session_id}/messages` | 메시지 전송 |
| GET | `/api/v1/chat/sessions/{session_id}/messages` | 메시지 목록 조회 |
| POST | `/api/v1/chat/sessions/{session_id}/feedback` | 챗봇 피드백 저장 |

## 알림/복약/일정/대시보드

| Method | Path | 설명 |
|---|---|---|
| GET | `/api/v1/notifications` | 알림 목록 조회 |
| PATCH | `/api/v1/notifications/{notification_id}/read` | 알림 읽음 처리 |
| DELETE | `/api/v1/notifications/{notification_id}` | 알림 삭제 |
| PATCH | `/api/v1/notifications/read-all` | 전체 읽음 처리 |
| GET | `/api/v1/notifications/unread-count` | 읽지 않은 알림 수 |
| GET | `/api/v1/notifications/settings` | 알림 설정 조회 |
| PATCH | `/api/v1/notifications/settings` | 알림 설정 수정 |
| POST | `/api/v1/notifications/remind` | 보호자 수동 리마인드 발송 |
| POST | `/api/v1/schedules/{schedule_id}/check` | 복약 완료 체크 |
| DELETE | `/api/v1/schedules/{schedule_id}/check` | 복약 체크 취소 |
| POST | `/api/v1/schedules/{schedule_id}/skip` | 복약 건너뜀 처리 |
| GET | `/api/v1/schedules/status` | 복약 현황 조회 |
| GET | `/api/v1/schedules/adherence` | 복약 이행률 조회 |
| POST | `/api/v1/calendar/hospital` | 병원 일정 생성 |
| GET | `/api/v1/calendar/hospital` | 병원 일정 조회 |
| PATCH | `/api/v1/calendar/hospital/{id}` | 병원 일정 수정 |
| DELETE | `/api/v1/calendar/hospital/{id}` | 병원 일정 삭제 |
| GET | `/api/v1/dashboard` | 관리자 대시보드 조회 |

## 비고
- `dashboard`는 ADMIN 권한이 필요합니다.
- `documents`, `guides`, `chat`, `notifications`는 환자-보호자 연동 관계를 서비스 레이어에서 검증합니다.
- 세부 Request/Response 필드는 Swagger 스키마를 단일 기준으로 사용하세요.
- 네이버 로그인은 현재 팀 구현 범위에서 제외(백로그)로 관리합니다.
