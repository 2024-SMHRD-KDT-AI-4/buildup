import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# 회원가입 요청 데이터 모델
class JoinRequest(BaseModel):
    user_id: str
    user_pw: str
    user_nickname: str
    user_email: str

# 회원가입 응답 데이터 모델
class JoinResponse(BaseModel):
    success: bool
    message: str

# 로그인 요청 데이터 모델
class LoginRequest(BaseModel):
    user_id: str
    user_pw: str

# 로그인 응답 데이터 모델
class LoginResponse(BaseModel):
    success: bool
    message: str
    user: dict = None

## 챗봇 요청 데이터 모델
class ChatBotRequest(BaseModel):
    user_id: str
    # 'chatbot_role'은 항상 "나"일 것이므로, 기본값을 설정하고 클라이언트가 변경할 수 없게 합니다.
    # 클라이언트가 요청 시 이 값을 보내지 않으면 자동으로 "나"가 됩니다.
    # 만약 다른 값을 보내면 Pydantic 유효성 검사에서 오류가 발생합니다.
    chatbot_role: str = Literal["나"]

    chatbot_text: str
    # created_at 필드는 서버(DB)에서 자동으로 생성하므로, 요청 모델에서는 제거합니다.

## 챗봇 응답 데이터 모델
class ChatBotResponse(BaseModel):
    chatbot_idx: int       # 데이터베이스의 고유 ID (AUTO_INCREMENT로 생성됨)
    user_id: str
    # 'chatbot_role'은 "나" 또는 "챗봇"이 될 수 있으므로, 단순히 str로 두는 것이 유연합니다.
    # 실제 값은 DB에서 가져온 데이터에 따라 결정됩니다.
    chatbot_role: str = Literal["챗봇"]
    chatbot_text: str
    created_at: datetime   # 데이터베이스의 TIMESTAMP가 Python의 datetime 객체로 매핑됩니다.


# 서명된 URL 요청 모델
class PresignedUrlRequest(BaseModel):
    object_key: str

# 서명된 URL 응답 모델
class PresignedUrlResponse(BaseModel):
    success: bool
    message: str
    presigned_url: str = None

# 이미지 업로드 API 응답 모델 
class ImageUploadResponse(BaseModel):
    success: bool  # 업로드 성공 여부 (True/False)
    message: str  # 결과 메시지
    s3_url: str = None  # S3에 저장된 이미지 URL (성공 시)
    presigned_url: str = None  # (현재 사용 안 함) 서명된 URL

# 개별 대화 메시지 응답 모델
class DialogueHistoryItem(BaseModel):
    user_id: str
    chatbot_role: str # "나" 또는 "챗봇"
    chatbot_text: str
    created_at: datetime

# 대화 이력 전체를 담을 응답 모델 
class DialogueHistoryResponse(BaseModel):
    success: bool # API 호출 성공 여부를 나타내는 필드 추가
    message: Optional[str] = None # 선택적으로 메시지를 담을 수 있는 필드 추가 (성공/실패 메시지 등)
    history: List[DialogueHistoryItem] # 대화 기록 리스트



# (필요하다면 다른 모델 클래스들도 여기에 추가)