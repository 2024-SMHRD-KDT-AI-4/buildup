import datetime
from fastapi import APIRouter, HTTPException, exceptions

# 수정된 임포트 (직접 임포트)
from database import database  # database.py에서 인스턴스를 가져오기
from schemas import (
    ChatBotRequest,
    ChatBotResponse,
    DialogueHistoryResponse,
    DialogueHistoryItem
)


router = APIRouter()

#/dialogue` 엔드포인트

from datetime import datetime
from fastapi import APIRouter, HTTPException
# import database # 가정: database 인스턴스가 잘 임포트되었다고 가정
from schemas import (
    ChatBotRequest,
    ChatBotResponse,
)

router = APIRouter()

@router.post("/dialogue", response_model=ChatBotResponse)
async def dialogue_handler(question_data: ChatBotRequest):

    print("Received data:", question_data)
    user_insert_sql = """
    INSERT INTO tb_chatbot(user_id, chatbot_role, chatbot_text, created_at)
    VALUES (:user_id, :chatbot_role, :chatbot_text, :created_at)
    """
    try:

        await database.execute(user_insert_sql, values={
            "user_id": question_data.user_id,
            "chatbot_role": question_data.chatbot_role, # "나"
            "chatbot_text": question_data.chatbot_text,
            "created_at": question_data.created_at, # Python에서 생성한 시간 사용
        })
    except Exception as e:
        print(f"사용자 메시지 저장 중 데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="Failed to save user message.")


    # ... (챗봇 엔진 답변 생성 로직은 동일) ...
    try:
        chatbot_answer_text = f"저에게 '{question_data.chatbot_text}' 라고 말씀하셨군요. 제가 도울 수 있는 부분은..." # 더미 응답
    except Exception as e:
        print(f"챗봇 엔진 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="Failed to get response from chatbot.")


    # 3. 챗봇의 답변을 DB에 저장
    # 이때, created_at 값을 Python 코드에서 직접 생성하여 사용할 수 있습니다.
    current_timestamp = datetime.now() # 현재 시각을 직접 생성

    chatbot_insert_sql = """
    INSERT INTO tb_chatbot(user_id, chatbot_role, chatbot_text, created_at)
    VALUES (:user_id, :chatbot_role, :chatbot_text, :created_at)
    """
    try:
        # DB에 created_at 값을 명시적으로 전달합니다.
        # 이렇게 하면 DB의 DEFAULT CURRENT_TIMESTAMP가 아닌, Python에서 생성한 시간이 저장됩니다.
        await database.execute(chatbot_insert_sql, values={
            "user_id": question_data.user_id,
            "chatbot_role": "챗봇", # 여기서는 챗봇의 답변이므로 "챗봇" 문자열을 직접 사용합니다.
            "chatbot_text": chatbot_answer_text,
            "created_at": current_timestamp, # Python에서 생성한 시간 사용
        })

        # DB 재조회 없이 바로 응답 모델 구성 및 반환
        return ChatBotResponse(
            user_id=question_data.user_id,
            chatbot_role="챗봇",
            chatbot_text=chatbot_answer_text,
            created_at=current_timestamp, # Python에서 생성한 시간 그대로 사용
        )

    except Exception as e:
        print(f"챗봇 답변 저장 중 데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="챗봇과 대화 중 오류가 발생했습니다(데이터베이스).")

# ====================================================================
# 새로운 대화 기록 조회 엔드포인트
# ====================================================================
@router.get("/dialogue/history/{user_id}", response_model=DialogueHistoryResponse)
async def get_dialogue_history(user_id: str): # 함수 매개변수로 user_id를 받습니다.
    """
    특정 user_id의 챗봇 대화 기록을 조회합니다.
    """
    # SQL 쿼리: user_id에 해당하는 모든 메시지를 created_at 기준으로 오름차순 정렬
    query = """
    SELECT user_id, chatbot_role, chatbot_text, created_at
    FROM tb_chatbot
    WHERE user_id = :user_id
    ORDER BY created_at ASC
    """

    try:
        # 데이터베이스에서 모든 해당 레코드를 가져옵니다.
        # fetch_all은 결과가 없으면 빈 리스트를 반환합니다.
        records = await database.fetch_all(query, {"user_id": user_id})

        # DB에서 가져온 레코드를 DialogueHistoryItem Pydantic 모델 리스트로 변환
        history = [
            DialogueHistoryItem(
                user_id=record["user_id"],
                chatbot_role=record["chatbot_role"],
                chatbot_text=record["chatbot_text"],
                created_at=record["created_at"],
            )
            for record in records
        ]

        # DialogueHistoryResponse 모델로 감싸서 반환
        return DialogueHistoryResponse(
            success=True,
            message="대화 기록 조회 성공",
            history=history
        )

    except Exception as e:
        # 데이터베이스 오류 또는 기타 예외 처리
        print(f"대화 기록 가져오기 오류 발생: {e}")
        # 클라이언트에게 500 Internal Server Error 반환
        raise HTTPException(status_code=500, detail="대화 기록을 가져오는 중 오류가 발생했습니다.")
 
        