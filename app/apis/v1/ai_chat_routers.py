from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies.security import get_request_user
from app.models.users import User
from app.core.config import Config
import httpx

router = APIRouter(prefix="/ai-chat", tags=["AI Chat"])
config = Config()


class ChatRequest(BaseModel):
    message: str
    patient_context: str | None = None


class ChatResponse(BaseModel):
    response: str


@router.post("", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_request_user),
) -> ChatResponse:
    """AI 챗봇과 대화"""
    if not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API 키가 설정되지 않았습니다.")

    system_prompt = """당신은 의료 복약 관리 전문 AI 어시스턴트 '약속이'입니다. 
환자와 보호자에게 복약 관련 정보, 생활습관 개선, 건강 관리에 대한 조언을 제공합니다.
친절하고 이해하기 쉬운 언어로 답변해주세요. 답변은 간결하게 3-4문장 이내로 작성하세요."""

    if request.patient_context:
        system_prompt += f"\n\n환자 정보: {request.patient_context}"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": request.message},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500,
                },
            )

            if response.status_code != 200:
                error_detail = response.text
                print(f"OpenAI API Error: {response.status_code} - {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"OpenAI API 오류: {response.status_code}",
                )

            data = response.json()
            ai_response = data["choices"][0]["message"]["content"]

            return ChatResponse(response=ai_response)

    except httpx.TimeoutException:
        print("OpenAI API Timeout")
        raise HTTPException(status_code=504, detail="AI 응답 시간 초과")
    except httpx.HTTPError as e:
        print(f"HTTP Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"네트워크 오류: {str(e)}")
    except KeyError as e:
        print(f"Response parsing error: {str(e)}")
        raise HTTPException(status_code=500, detail="AI 응답 파싱 오류")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 챗봇 오류: {str(e)}")
