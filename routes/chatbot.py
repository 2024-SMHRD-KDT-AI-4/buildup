# chatbot.py

import datetime
import os
import logging # 로깅 모듈 추가
from fastapi import APIRouter, HTTPException
from database import database # 데이터베이스 인스턴스 (경로 확인 필요)
from schemas import ( # Pydantic 모델 (경로 확인 필요)
    ChatBotRequest,
    ChatBotResponse,
    DialogueHistoryResponse,
    DialogueHistoryItem,
    SkinAdviceRequest, # 피부 조언 요청 시 사용될 수 있음
    SkinAdviceResponse # 피부 조언 응답 시 사용될 수 있음
)
import google.generativeai as genai
from typing import Optional

# --- 로깅 설정 ---
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)
# 위 설정은 main.py에서 한 번만 하는 것이 좋습니다. 여기서는 이미 설정되었다고 가정합니다.
# 대신, 각 라우터 파일에서는 getLogger를 통해 로거 인스턴스만 가져와 사용하는 것이 일반적입니다.
logger = logging.getLogger("uvicorn.error") # FastAPI/Uvicorn의 기본 로거 사용 또는 별도 로거 설정


# --- Gemini API 설정 ---
# 중요: .env 파일에 GEMINI_API_KEY=여러분의API키 형태로 저장하고,
# main.py 등 애플리케이션 시작 지점에서 load_dotenv()를 호출해야 합니다.
gemini_model = None
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY 환경 변수가 .env 파일 또는 시스템에 설정되지 않았습니다. Gemini API 호출이 실패할 수 있습니다.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # 필요에 따라 안전 설정 조정
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        gemini_model = genai.GenerativeModel(
            model_name="gemini-1.5-flash-latest", # 또는 사용 가능한 다른 최신/적합한 모델
            safety_settings=safety_settings,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7, # 답변의 다양성 조절 (0.0 ~ 1.0)
                # max_output_tokens=800, # 답변 최대 길이 (필요시 설정)
            )
        )
        logger.info("Gemini 모델 (chatbot.py용)이 성공적으로 로드되었습니다.")
    except Exception as e:
        logger.error(f"Gemini 모델 (chatbot.py용) 초기화 중 심각한 오류 발생: {e}", exc_info=True)
        # gemini_model은 None으로 유지되어 API 호출 시 에러를 발생시키도록 합니다.

router = APIRouter()

async def get_recent_dialogue_history(user_id: str, limit: int = 5) -> str:
    """
    특정 사용자의 최근 대화 기록을 가져와 Gemini 프롬프트용으로 포맷팅합니다.
    """
    history_query = """
    SELECT chatbot_role, chatbot_text
    FROM tb_chatbot
    WHERE user_id = :user_id
    ORDER BY created_at DESC
    LIMIT :limit
    """
    try:
        records = await database.fetch_all(history_query, {"user_id": user_id, "limit": limit})
        formatted_history = ""
        if records:
            for record in reversed(records): # 시간 순서대로 (오래된 메시지가 먼저)
                role_display = "사용자" if record["chatbot_role"] in ["나", "user"] else "챗봇"
                formatted_history += f"{role_display}: {record['chatbot_text']}\n"
        return formatted_history
    except Exception as e:
        logger.error(f"대화 기록 조회 중 오류 발생 (user_id: {user_id}): {e}", exc_info=True)
        return "" # 오류 발생 시 빈 문자열 반환

def create_gemini_prompt(user_input: str, skin_type: Optional[str] = None, dialogue_history: str = "") -> str:
    """
    사용자 입력과 상황에 따라 Gemini API 프롬프트를 생성합니다.
    """
    if skin_type and skin_type.lower() != "알 수 없음" and skin_type.lower() != "없음":
        # 피부 타입 정보가 있고, 유효한 경우 -> 화장품 추천 프롬프트
        # (이전에 사용자님이 작성해주신 상세 프롬프트를 여기에 사용합니다)
        # personal_color_tone 정보도 필요하다면 skin_type처럼 인자로 받아 프롬프트에 포함시킵니다.
        logger.info(f"피부 타입 기반 추천 프롬프트 생성: {skin_type}")
        prompt = f"""
1. 당신은 사용자의 피부 타입 "{skin_type}"에 따라 기초 화장품을 추천하고 설명해주는 올리브영 직원입니다.
2. 형식은 "당신의 피부 타입은 🌼{skin_type}🌼 입니다. {skin_type} 피부 타입은 {{자세한 특징}}을 가지고 있어 {{주의점}}에 유의해야 합니다. 당신을 위한 기초 화장품과 사용 순서를 알려드릴게요" 로 시작해주세요.
3. 고객에게 화장품을 추천하고 구매하도록 유도하는 것이 목표입니다. 친근하며 부드럽고 설득력 있는 톤으로, 가독성 좋게 설명해주세요. 화장품 초보도 이해하도록 제품 필요성과 기능, 바르는 순서를 설명합니다. 피부 타입별 특징과 연결하여 설명하고, 피부 타입별 대표 키워드 3가지를 포함하여 이야기해주세요.
4. 올리브영 입점 브랜드 중심으로 각 제품은 7만원 이하로 추천합니다. 추천 목록은 "🧼클렌저, 💦스킨/토너, 💧앰플/세럼, 🧴로션, 🧈크림, 🛀마스크팩" 입니다. 제품 이미지 대신 "[카테고리: 제품명]" 형식으로 표시하고, 가격대, 올리브영 입점 여부("O" 또는 "확인 필요")를 포함하여 전체 답변은 1500자 이내로 요약해주세요.
6. 마무리로 꼭 필요한 기초 제품 3가지(클렌저, 팩 제외) 이름 목록과 바르는 순서, 그리고 "단계 별로 가볍게 두드려 모두 흡수시켜 주신 후, 다음 제품을 발라주세요." 멘트를 포함해주세요.
7. 마지막은 살갑고 친절한 멘트 한 줄로 마무리해주세요.

이전 대화:
{dialogue_history if dialogue_history else "없음"}

현재 사용자 요청: {user_input} (이 사용자는 "{skin_type}" 피부입니다.)

챗봇 답변:
        """
    else:
        # 일반 대화 프롬프트
        logger.info("일반 대화 프롬프트 생성")
        prompt = f"""
        당신은 "SkinThera"라는 뷰티 및 피부 건강 관련 서비스를 제공하는 AI 챗봇입니다.
        당신의 역할은 사용자에게 친절하고, 전문적이며, 도움이 되는 답변을 한국어로 제공하는 것입니다.
        다음은 사용자와의 이전 대화 내용입니다. 이를 참고하여 현재 사용자의 질문에 가장 적절하고 자연스러운 답변을 생성해주세요.
        만약 이전 대화 내용이 없다면, 현재 질문에만 집중하여 답변해주세요.
        매우 구체적이고 개인화된 분석(예: 특정 제품의 상세 비교, 이미지 기반 분석)은 사용자가 별도의 전문 기능을 사용하도록 안내해주세요.

        이전 대화:
        {dialogue_history if dialogue_history else "없음"}

        현재 사용자 질문: {user_input}

        챗봇 답변:
        """
    return prompt

@router.post("/dialogue", response_model=ChatBotResponse)
async def dialogue_handler(request_data: ChatBotRequest):
    logger.info(f"대화 요청 받음: 사용자 ID {request_data.user_id}, 메시지: {request_data.chatbot_text}")

    # 1. 사용자 메시지를 DB에 저장
    user_insert_sql = """
    INSERT INTO tb_chatbot(user_id, chatbot_role, chatbot_text, created_at)
    VALUES (:user_id, :chatbot_role, :chatbot_text, :created_at)
    """
    try:
        await database.execute(user_insert_sql, values={
            "user_id": request_data.user_id,
            "chatbot_role": request_data.chatbot_role,
            "chatbot_text": request_data.chatbot_text,
            "created_at": request_data.created_at, # 프론트에서 생성한 시간 (ISO 문자열)
        })
        logger.info(f"사용자 메시지 저장 성공 (사용자 ID: {request_data.user_id})")
    except Exception as e:
        logger.error(f"사용자 메시지 저장 중 데이터베이스 오류 발생: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="사용자 메시지를 데이터베이스에 저장하는데 실패했습니다.")

    # 2. 챗봇 답변 생성
    chatbot_answer_text = "죄송합니다. 현재 답변을 드리기 어렵습니다. 잠시 후 다시 시도해주세요." # 기본 오류 메시지

    if not gemini_model:
        logger.error("Gemini 모델이 로드되지 않아 지능적인 답변을 생성할 수 없습니다.")
    else:
        try:
            user_input = request_data.chatbot_text or "" # 혹시 None일 경우 대비

            # --- 의도 분류 및 정보 추출 (간단한 예시) ---
            # 실제로는 더 정교한 NLU/Dialogflow 로직이 필요할 수 있습니다.
            # 여기서는 사용자가 skin_type 정보를 ChatBotRequest에 직접 담아 보낸다고 가정하거나,
            # 또는 user_id를 통해 DB에서 사용자의 피부 분석 결과를 가져온다고 가정합니다.
            # SkinAnalysisResult 페이지에서는 /chatbot/skin_advice를 호출하는 것이 더 명확합니다.
            # 이 /dialogue 엔드포인트는 일반 대화에 더 집중하거나,
            # 사용자가 "내 피부는 건성이야" 같이 자연어로 말했을 때 파싱하는 로직이 필요합니다.

            # 여기서는 ChatBotRequest에 skin_type 필드가 선택적으로 온다고 가정 (schemas.py 수정 필요)
            # 또는 React에서 특정 버튼 클릭 시 skin_type 정보를 담아 이 API를 호출한다고 가정
            # current_skin_type = request_data.skin_type if hasattr(request_data, 'skin_type') else None
            
            # 임시: 여기서는 사용자가 "건성 피부인데..." 라고 말하면 피부 타입으로 인식하는 매우 간단한 예시
            # 실제로는 더 정교한 방법이 필요합니다.

            detected_skin_type = None
            if "건성" in user_input:
                detected_skin_type = "건성"
            elif "지성" in user_input:
                detected_skin_type = "지성"
            elif "복합성" in user_input: # "복합건성", "복합지성" 등 더 세분화 가능
                detected_skin_type = "복합성"
            # (다른 피부 타입 키워드 추가)

            dialogue_history = await get_recent_dialogue_history(request_data.user_id)
            prompt = create_gemini_prompt(user_input, skin_type=detected_skin_type, dialogue_history=dialogue_history)
            
            logger.info(f"Gemini API 요청 프롬프트 (일부): {prompt[:300]}...")
            response = await gemini_model.generate_content_async(prompt)

            if not response.candidates or not response.candidates[0].content.parts:
                logger.warning("Gemini API로부터 유효한 응답(candidates)을 받지 못했습니다.")
            else:
                chatbot_answer_text = response.text
                logger.info(f"Gemini API 응답 성공 (일부): {chatbot_answer_text[:200]}...")
        
        except Exception as e:
            logger.error(f"Gemini API 호출 또는 응답 처리 중 오류 발생: {e}", exc_info=True)
            if "quota" in str(e).lower():
                 chatbot_answer_text = "현재 많은 사용자가 서비스를 이용 중입니다. 잠시 후 다시 시도해주시면 감사하겠습니다."
            # 다른 특정 오류에 대한 처리 추가 가능

    # 3. 챗봇의 답변을 DB에 저장
    # (오류 발생 시에도 chatbot_answer_text는 기본 오류 메시지 또는 특정 오류 메시지를 가짐)
    response_timestamp = datetime.datetime.now() # 답변 생성 및 저장 시점의 시간
    chatbot_insert_sql = """
    INSERT INTO tb_chatbot(user_id, chatbot_role, chatbot_text, created_at)
    VALUES (:user_id, :chatbot_role, :chatbot_text, :created_at)
    """
    try:
        await database.execute(chatbot_insert_sql, values={
            "user_id": request_data.user_id,
            "chatbot_role": "챗봇",
            "chatbot_text": chatbot_answer_text,
            "created_at": response_timestamp,
        })
        logger.info(f"챗봇 답변 저장 성공 (사용자 ID: {request_data.user_id})")
    except Exception as e:
        logger.error(f"챗봇 답변 저장 중 데이터베이스 오류 발생: {e}", exc_info=True)
        # 이 오류는 사용자에게 이미 생성된 답변을 보내는 데는 영향이 없도록 처리할 수 있음 (로깅만)
        # 하지만 심각한 오류라면 여기서도 HTTPException을 발생시켜야 할 수 있음

    return ChatBotResponse(
        user_id=request_data.user_id,
        chatbot_role="챗봇",
        chatbot_text=chatbot_answer_text,
        created_at=response_timestamp,
    )

# --- 피부 조언 전용 엔드포인트 (SkinAnalysisResult 페이지에서 사용) ---
# 이 엔드포인트는 React의 SkinAnalysisResult 페이지에서 피부 분석 결과를 바탕으로
# 상세한 화장품 추천을 받을 때 사용합니다.
@router.post("/skin_advice", response_model=SkinAdviceResponse)
async def skin_advice_handler(advice_request: SkinAdviceRequest):
    logger.info(f"피부 조언 요청 받음: 사용자 ID {advice_request.user_id}, 피부 타입 {advice_request.predicted_skin_type}, 퍼스널 컬러 {advice_request.personal_color_tone}")

    if not gemini_model:
        logger.error("Gemini 모델이 로드되지 않아 피부 조언을 생성할 수 없습니다.")
        raise HTTPException(status_code=503, detail="AI 모델을 현재 사용할 수 없습니다. 관리자에게 문의하세요.")

    # 상세 프롬프트 구성 (이전 답변에서 사용된 상세 프롬프트 사용)
    prompt = create_gemini_prompt(
        user_input=f"{advice_request.predicted_skin_type} 피부와 {advice_request.personal_color_tone} 퍼스널 컬러에 맞는 화장품 추천", # 사용자의 요청을 명시적으로 구성
        skin_type=advice_request.predicted_skin_type,
        # personal_color_tone은 create_gemini_prompt 내부에서 피부 타입 프롬프트에 활용될 수 있도록 전달하거나,
        # 프롬프트 문자열 자체에 advice_request.personal_color_tone을 직접 삽입할 수 있습니다.
        # 여기서는 create_gemini_prompt 함수가 skin_type을 받아서 해당 프롬프트를 사용하도록 되어 있습니다.
        # 필요하다면 create_gemini_prompt 함수를 수정하여 personal_color_tone도 명시적으로 다루도록 할 수 있습니다.
    )
    
    # 화장품 추천 프롬프트는 상세하므로, 이전 대화 내용은 여기서는 생략하거나 다르게 활용할 수 있습니다.
    # 지금 create_gemini_prompt는 skin_type이 주어지면 화장품 추천 프롬프트를 사용합니다.

    advice_text = "죄송합니다. 현재 맞춤형 피부 조언을 드리기 어렵습니다." # 기본 오류 메시지
    try:
        logger.info(f"Gemini API 요청 프롬프트 (피부 조언용, 일부): {prompt[:300]}...")
        response = await gemini_model.generate_content_async(prompt)

        if not response.candidates or not response.candidates[0].content.parts:
            logger.warning("Gemini API로부터 유효한 응답(candidates)을 받지 못했습니다. (피부 조언)")
        else:
            advice_text = response.text
            logger.info(f"Gemini API 피부 조언 응답 성공 (일부): {advice_text[:200]}...")
    
    except Exception as e:
        logger.error(f"Gemini API 피부 조언 호출 또는 응답 처리 중 오류 발생: {e}", exc_info=True)
        if "quota" in str(e).lower():
             advice_text = "현재 많은 사용자가 서비스를 이용 중입니다. 잠시 후 다시 시도해주시면 감사하겠습니다."

    # 이 조언을 tb_chatbot에 저장할 수도 있습니다 (선택 사항)
    response_timestamp = datetime.datetime.now()
    # ... (필요시 DB 저장 로직 추가) ...

    return SkinAdviceResponse(
        user_id=advice_request.user_id,
        advice=advice_text,
        created_at=response_timestamp
    )


# --- 대화 기록 조회 엔드포인트 ---
@router.get("/dialogue/history/{user_id}", response_model=DialogueHistoryResponse)
async def get_dialogue_history(user_id: str):
    logger.info(f"대화 기록 조회 요청: 사용자 ID {user_id}")
    query = """
    SELECT user_id, chatbot_role, chatbot_text, created_at
    FROM tb_chatbot
    WHERE user_id = :user_id
    ORDER BY created_at ASC
    """
    try:
        records = await database.fetch_all(query, {"user_id": user_id})
        history = [
            DialogueHistoryItem(
                user_id=record["user_id"],
                chatbot_role=record["chatbot_role"],
                chatbot_text=record["chatbot_text"],
                created_at=record["created_at"],
            )
            for record in records
        ]
        logger.info(f"대화 기록 조회 성공 (사용자 ID: {user_id}, 기록 수: {len(history)})")
        return DialogueHistoryResponse(
            success=True,
            message="대화 기록 조회 성공",
            history=history
        )
    except Exception as e:
        logger.error(f"대화 기록 가져오기 오류 발생 (사용자 ID: {user_id}): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="대화 기록을 가져오는 중 오류가 발생했습니다.")