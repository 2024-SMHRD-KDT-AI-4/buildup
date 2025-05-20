from pydantic import BaseModel

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

# (필요하다면 다른 모델 클래스들도 여기에 추가)