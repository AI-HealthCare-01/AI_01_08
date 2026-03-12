#!/usr/bin/env bash
set -u

BASE_URL="${BASE_URL:-http://localhost:8000}"
SIGNUP_URL="$BASE_URL/api/v1/auth/signup"
RANDOM_EMAIL="manual.$(date +%s)@gmail.com"

run_case() {
  local name="$1"
  local payload="$2"

  echo "\n== $name =="
  local status
  status=$(curl -s -o /tmp/signup_response.json -w "%{http_code}" \
    -X POST "$SIGNUP_URL" \
    -H "Content-Type: application/json" \
    -d "$payload")

  echo "HTTP $status"
  cat /tmp/signup_response.json
  echo
}

invalid_payload='{
  "email": "tes.com",
  "password": "Password123!",
  "name": "테스터",
  "gender": "MALE",
  "birth_date": "1990-01-01",
  "phone_number": "01012345678"
}'

valid_payload="{
  \"email\": \"$RANDOM_EMAIL\",
  \"password\": \"Password123!\",
  \"name\": \"테스터\",
  \"gender\": \"MALE\",
  \"birth_date\": \"1990-01-01\",
  \"phone_number\": \"01012345679\"
}"

run_case "INVALID EMAIL (tes.com) - should be 422" "$invalid_payload"
run_case "VALID EMAIL - should be 201" "$valid_payload"

echo "\nDone. Endpoint: $SIGNUP_URL"
