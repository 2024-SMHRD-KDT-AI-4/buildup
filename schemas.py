# import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from datetime import datetime 
from datetime import date # Date 타입은 datetime 모듈의 date를 import 해야 합니다.

# 회원가입 요청 데이터 모델
class JoinRequest(BaseModel):
    user_id: str
    user_pw: str
    user_nickname: str
    user_email: str
    user_sex: Literal["남성", "여성"]
    user_birthdate: str        

# 회원가입 응답 데이터 모델
class JoinResponse(BaseModel):
    success: bool
    message: str

# 로그인 요청 데이터 모델
class LoginRequest(BaseModel):
    user_id: str
    user_pw: str

# 로그인 응답의 사용자 데이터 모델
class User(BaseModel):
    id: str
    nickname: str
    email: str
    sex: str
    birthdate: date
    joinDate: datetime
    role: str

# 로그인 응답 데이터 모델
class LoginResponse(BaseModel):
    success: bool
    message: str
    user: User = None  # None은 로그인이 실패한 경우를 대비한 기본값

# 아이디 체크 요청 데이터 모델
class CheckIDRequest(BaseModel):
    user_id: str

# 아이디 체크 응답 데이터 모델
class CheckIDResponse(BaseModel):
    success: bool
    possible: bool
    message: str    

# 비밀번호 체크 요청 데이터 모델
class CheckPWRequest(BaseModel):
    user_id: str
    user_pw: str

# 비밀번호 체크 응답 데이터 모델
class CheckPWResponse(BaseModel):
    success: bool
    message: str

# 비밀번호 변경 요청 데이터 모델
class UpdatePWRequest(BaseModel):
    user_id: str
    user_pw: str
    user_new_pw: str

# 비밀번호 변경 응답 데이터 모델
class UpdatePWResponse(BaseModel):
    success: bool
    message: str

# 비밀번호 변경 요청 데이터 모델
class UpdateNicknameRequest(BaseModel):
    user_id: str
    user_new_nickname: str

# 비밀번호 변경 응답 데이터 모델
class ServerResponse(BaseModel):
    success: bool
    message: str



##################################



## 챗봇 요청 데이터 모델
class ChatBotRequest(BaseModel):
    user_id: str
    chatbot_role: str = "나"  # 기본값: "나"
    chatbot_text: Optional[str] = None
    created_at: datetime

## 챗봇 응답 데이터 모델
class ChatBotResponse(BaseModel):
    #chatbot_idx: Optional[int]       # 데이터베이스의 고유 ID (AUTO_INCREMENT로 생성됨)
    user_id: str
    # 'chatbot_role'은 "나" 또는 "챗봇"이 될 수 있으므로, 단순히 str로 두는 것이 유연합니다.
    # 실제 값은 DB에서 가져온 데이터에 따라 결정됩니다.
    chatbot_role: Literal["챗봇"] = "챗봇"
    chatbot_text: str
    created_at: datetime   # 데이터베이스의 TIMESTAMP가 Python의 datetime 객체로 매핑됩니다.

    class Config:
        arbitrary_types_allowed = True


# 서명된 URL 요청 모델
class PresignedUrlRequest(BaseModel):
    object_key: str

# 서명된 URL 응답 모델
class PresignedUrlResponse(BaseModel):
    success: bool
    message: str
    presigned_url: str = None

# 이미지 업로드 API 요청 모델 
class ImageUploadRequest(BaseModel):
    user_id: str
    created_at: datetime


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

# 이미지 분석 요청 데이터 모델
class AnalyzeS3ImageRequest(BaseModel):
    s3_url: str
    filename: str

# 이미지 분석 응답 데이터 모델
class AnalyzeS3ImageResponse(BaseModel):
    message: str
    filename: str
    personal_color_tone: str # 분석 결과가 문자열이라고 가정

class SkinAdviceRequest(BaseModel):
    user_id: str # 사용자 식별
    predicted_skin_type: str
    personal_color_tone: str # React에서 넘어온 personal_color_tone
    # s3_url: Optional[str] = None # 필요하다면 이미지 URL도 전달 가능
    # created_at_from_analysis: datetime.datetime # 분석 결과 생성 시각, 필요하다면 전달

class SkinAdviceResponse(BaseModel):
    user_id: str
    advice: str # Gemini API로부터 받은 추천 내용 전체 텍스트
    created_at: datetime # 조언 생성 시각
# 요청 모델 정의
class PastAnalysisRequest(BaseModel):
    user_id: str

# 응답 모델 정의 (선택 사항)
class PastAnalysisResponse(BaseModel):
    success: bool
    message: str
    data: list[dict] | None
