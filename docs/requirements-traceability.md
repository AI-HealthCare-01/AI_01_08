# 요구사항 추적표

기준 시점: `2026-03-23`  
원본은 팀 요구사항 정의서를 기준으로 하며, 아래는 코드 반영 상태를 문서화한 최소 추적표입니다.

## 상태 기준
- `구현`: 요구사항 핵심 기능이 코드와 API로 동작
- `부분`: 일부 동작하지만 정의서 조건이 전부 충족되지는 않음
- `백로그`: 현재 브랜치에서 구현 근거를 찾지 못함

## 인증/권한

| ID | 상태 | 근거 (요약) | 보완 필요 |
|---|---|---|---|
| REQ-AUTH-001 | 부분 | `POST /api/v1/auth/signup`, `AuthService.signup` | 닉네임, 휴대폰/이메일 인증, 닉네임 중복확인 |
| REQ-AUTH-002 | 부분 | `POST /api/v1/auth/login`, JWT 발급 + refresh cookie | 실패 사유 상세 분리(이메일 미존재/비번 불일치) |
| REQ-AUTH-003 | 부분 | 카카오 OAuth (`/auth/social/kakao/*`) | 필수 동의 데이터(휴대폰/생년/성별/프로필) 저장 강화 |
| REQ-AUTH-004 | 백로그 | 네이버 로그인은 현재 팀 구현 범위 제외 | 네이버 OAuth 플로우 신규 구현 |
| REQ-AUTH-005 | 부분 | `POST /api/v1/auth/logout` 쿠키 삭제 | refresh token 서버 무효화 정책 |
| REQ-AUTH-006 (역할) | 부분 | 가입 시 역할 선택/권한 체크(`user_has_role`) | 역할 변경 전용 API |
| REQ-AUTH-007 (권한검증) | 구현 | 요청 사용자 검증 + 환자/연동 접근 제어 | - |
| REQ-AUTH-006 (토큰갱신) | 부분 | `GET /api/v1/auth/token/refresh` | 저장소 기반 refresh 관리 정책 명문화 |
| REQ-AUTH-007 (비번재설정) | 부분 | `POST /api/v1/auth/reset-password` | 이메일 링크/토큰 기반 재설정 |
| REQ-AUTH-008 | 구현 | `DELETE /api/v1/users/me` 비활성화 처리 | 탈퇴 후 데이터 정책 문서화 |
| REQ-AUTH-009 | 백로그 | 코드상 약관 동의 플로우 미확인 | 가입 시 약관 동의 필수화 |

## 사용자/문서/OCR/약물

| ID | 상태 | 근거 (요약) | 보완 필요 |
|---|---|---|---|
| REQ-USER-001 | 구현 | `/users/me/health-profile` 생성 | - |
| REQ-USER-002 | 구현 | `/users/me/health-profile` 조회/수정 | - |
| REQ-USER-003 | 구현 | `patient_profile_service` BMI 계산 | - |
| REQ-USER-004 | 구현 | `/users/invite-code` 생성/폐기, TTL | - |
| REQ-USER-005 | 구현 | `/users/link` 초대코드 연동 | - |
| REQ-USER-006 | 구현 | `/users/links` 목록 조회 | - |
| REQ-USER-007 | 구현 | `/users/links/{link_id}` 연동 해제 | - |
| REQ-USER-008 | 구현 | 문서 업로드 시 대상 환자 귀속 (`upload_document`) | - |
| REQ-DOC-001 | 구현 | 문서 soft delete (`status=deleted`) | - |
| REQ-DOC-002 | 구현 | 문서 목록 필터(`/documents`) | - |
| REQ-DOC-003 | 구현 | OCR 비동기 처리 + 상태 조회 + 재개/재시도 | - |
| REQ-DOC-004 | 구현 | OCR raw text 저장(`OcrRawText`) | - |
| REQ-DOC-005 | 구현 | OCR 결과 약 정보 구조화(`ExtractedMed`) | - |
| REQ-DOC-006 | 구현 | `/documents/{id}/drugs` | - |
| REQ-DOC-007 | 구현 | `/documents/{id}/drugs` 수정/확정 | - |
| REQ-DOC-008 | 구현 | `/documents/{id}/retry` + 실패코드 | - |
| REQ-DOC-009 | 구현 | `/documents/barcodes/decode` | - |
| REQ-DRUG-001 | 구현 | `/documents/mfds/search` + 자동 매칭 로직 | - |
| REQ-DRUG-002 | 구현 | MFDS/DUR/최대투여량 조회(`MFDSClient`) | - |
| REQ-DRUG-003 | 부분 | `DrugInfoCache` 저장 + `expires_at` | `fetched_at` 명시 필드/정책 |
| REQ-DRUG-004 | 백로그 | Redis 캐시 전용 계층 미구현 | TTL 정책 포함 캐시 계층 |
| REQ-DRUG-005 | 구현 | 약명 정규화(`normalize_drug_name`) | - |
| REQ-DRUG-010 | 부분 | DUR 데이터 수집/노출 경로 존재 | 자동 판별 결과 저장/표시 정책 구체화 |
| REQ-DRUG-011 | 부분 | DUR 경고 조회/노출 로직 존재 | 경고 생성 파이프라인 고도화 |
| REQ-DRUG-012 | 부분 | 최대투여량 조회는 존재 | 사용자 총 복용량 초과 자동 판정 |
| REQ-DRUG-013 | 부분 | 약 변경 시 일부 재조회 로직 존재 | 전 트리거 재계산 표준화 |

## 가이드/챗봇/확장/관리자/NFR

| ID | 상태 | 근거 (요약) | 보완 필요 |
|---|---|---|---|
| REQ-GUIDE-001 | 구현 | `/guides/generate` + `ai_tasks` 큐 | - |
| REQ-GUIDE-002 | 구현 | 프로필/약물/MFDS/DUR 기반 컨텍스트 조합 | - |
| REQ-GUIDE-003 | 구현 | 가이드 구조 검증(`guide_validation`) | - |
| REQ-GUIDE-004 | 구현 | 건강 프로필 반영 프롬프트 생성 | - |
| REQ-GUIDE-005 | 부분 | 연령 기반 audience 분기 존재 | 60세 기준/고령자 전용 템플릿 강화 |
| REQ-GUIDE-006 | 구현 | 가이드 text/json DB 저장 | - |
| REQ-GUIDE-007 | 구현 | 목록/상세 조회 + 권한검증 | - |
| REQ-GUIDE-008 | 구현 | 재생성/버전 관리 | - |
| REQ-GUIDE-009 | 구현 | `caregiver_summary` 저장/응답 | - |
| REQ-GUIDE-010 | 구현 | MFDS/DUR/RAG 근거 기반 + 면책 문구 | - |
| REQ-CHAT-001 | 구현 | 세션/메시지 API + 비동기 답변 | - |
| REQ-CHAT-002 | 구현 | 약/가이드 컨텍스트 사용 | - |
| REQ-CHAT-003 | 구현 | 최근 N턴 히스토리 반영(`CHAT_HISTORY_TURNS`) | - |
| REQ-CHAT-004 | 구현 | 역할 기반 응답 분기 | - |
| REQ-CHAT-005 | 구현 | 메시지/피드백 저장 | - |
| REQ-CHAT-006 | 구현 | 세션 생성 시 대상 환자 지정 | - |
| REQ-CHAT-007 | 구현 | 응급 키워드 기반 안전 안내 | - |
| REQ-EXT-001 | 부분 | 복약 스케줄은 문서 확정 시 생성 | 수동 등록(Create) API |
| REQ-EXT-002 | 백로그 | 스케줄 수정/삭제 API 미확인 | CRUD API 추가 |
| REQ-EXT-003 | 구현 | `/schedules/{id}/check`, `/skip`, undo | - |
| REQ-EXT-004 | 구현 | `/schedules/status` | - |
| REQ-EXT-005 | 부분 | 환자 기준 조회는 가능 | 보호자 전용 정책/화면 명확화 |
| REQ-EXT-006 | 구현 | `/schedules/adherence` | - |
| REQ-EXT-007 | 구현 | 알림 설정 API(`/notifications/settings`) | - |
| REQ-EXT-008 | 구현 | `/notifications/remind` 수동 리마인드 | - |
| REQ-EXT-009 | 부분 | 워커 주기 점검/미복용 알림 생성 로직 | 유예시간 파라미터 명시 |
| REQ-EXT-010 | 부분 | 자동 알림 워커 존재 | 운영 정책/메시지 표준화 |
| REQ-EXT-011 | 부분 | 미복용 알림 생성 로직 존재 | 기준값 설정 외부화 |
| REQ-EXT-012 | 구현 | 병원 일정 CRUD(`/calendar/hospital`) | - |
| REQ-EXT-013 | 구현 | 병원 일정 조회 + 환자 기준 조회 | - |
| REQ-EXT-014 | 백로그 | 약 이미지 분류 API 미확인 | 이미지 분류 파이프라인 |
| REQ-EXT-015 | 백로그 | 분류 결과 반환 미확인 | 모델 추론/응답 스키마 |
| REQ-EXT-016 | 백로그 | 분류 결과 저장 미확인 | 저장 모델/API |
| REQ-ADMIN-001 | 구현 | `/dashboard` 관리자 지표 조회 | 지표 정의/운영 대시보드 확장 |
| REQ-ADMIN-002 | 부분 | 챗봇 피드백 저장 구현 | 가이드 피드백/오류신고 통합 |
| NFR-HCG-001 | 구현 | API/Worker/Queue 분리 아키텍처 | - |
| NFR-HCG-002 | 부분 | `CHAT_SLOW_REPLY_SECONDS` 설정 존재 | SLO 측정/알림 체계 |
| NFR-HCG-003 | 구현 | 주요 키 환경변수 관리 | - |
| NFR-HCG-004 | 구현 | RBAC + 연동관계 기반 접근 통제 | - |
| NFR-HCG-005 | 부분 | 로깅은 존재 | 구조화 로그/추적ID 표준화 |
| NFR-HCG-006 | 구현 | FAILED 상태 저장 + 재시도 로직 | - |
| NFR-HCG-007 | 구현 | 가이드/챗봇 면책 문구 적용 | - |
| NFR-HCG-008 | 구현 | EC2 단일서버 + Compose 배포 | - |
| NFR-HCG-009 | 부분 | Nginx 외 포트 노출 가능 설정 존재 | SG로 DB/Redis 외부 차단 필수 |
| NFR-HCG-010 | 구현 | 파일 확장자/크기 제한(10MB) 적용 | MIME/악성파일 탐지 강화 |
| NFR-HCG-011 | 구현 | 근거 기반 생성 + 검증/면책 | - |
| NFR-HCG-012 | 구현 | 검증 실패 시 `GUIDE_VALIDATION_FAILED` | - |
| NFR-HCG-013 | 부분 | MFDS 캐시 사용 + 실패 예외 처리 | `UNVERIFIED` 상태값 명시 |
