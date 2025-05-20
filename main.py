from fastapi import FastAPI, HTTPException ,Request, File, UploadFile
from database import database  # database.py에서 인스턴스를 가져오기
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from argon2 import PasswordHasher
from argon2 import exceptions
from dotenv import load_dotenv
load_dotenv()

import boto3
import os
import logging
from typing import Annotated
# 수정된 임포트 (직접 임포트)
from schemas import (
    JoinRequest,
    JoinResponse,
    LoginRequest,
    LoginResponse,
    PresignedUrlRequest,
    PresignedUrlResponse,
    ImageUploadResponse
)

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
# FastAPI 인스턴스 생성
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용. 필요시 특정 도메인으로 제한.
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용.
    allow_headers=["*"],  # 모든 헤더 허용.
)

ps = PasswordHasher()



# 이미지 업로드 단
# 환경 변수에서 자격 증명 가져오기 (권장)
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    region_name=os.environ.get("AWS_REGION")
)

# 환경 변수에서 S3 버킷 이름 가져오기
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

if not S3_BUCKET_NAME:
    raise ValueError("S3_BUCKET_NAME 환경 변수가 설정되지 않았습니다.")


# 이미지 업로드 API 엔드포인트 정의
@app.post("/upload/image_base64", response_model=ImageUploadResponse)
async def upload_image(file: Annotated[UploadFile, File()]):
    try:
        # UploadFile 객체에서 이미지 파일 내용 읽기 (비동기 방식)
        contents = await file.read()
        # 업로드된 파일의 원래 이름 가져오기
        file_name = file.filename
        # S3에 저장될 객체 키 생성 (images/ 폴더 아래 원래 파일 이름으로 저장)
        s3_key = f"images/{file_name}"

        # Boto3 클라이언트를 사용하여 S3에 객체(이미지) 업로드
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,  # 대상 S3 버킷 이름
            Key=s3_key,             # S3에 저장될 객체 키
            Body=contents           # 업로드할 이미지 파일 내용 (bytes)
        )

        # 업로드 성공 시 S3 이미지 URL 생성
        s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"

        # 성공 응답 반환
        return {
            "success": True,
            "message": f"이미지 '{file_name}' 업로드 성공",
            "s3_url": s3_url
        }
    except Exception as e:
        # 오류 발생 시 로깅
        logging.error(f"S3 이미지 업로드 오류: {e}")
        # HTTP 예외 발생 (500 Internal Server Error)
        raise HTTPException(status_code=500, detail="이미지 업로드 실패")


@app.post("/get/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(request_data: PresignedUrlRequest):
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': S3_BUCKET_NAME, 'Key': request_data.object_key},
            ExpiresIn=3600  # URL 유효 시간 (초) - 필요에 따라 조정
        )
        return {"success": True, "message": "서명된 URL 생성 성공", "presigned_url": presigned_url}
    except Exception as e:
        logging.error(f"서명된 URL 생성 오류: {e}")
        raise HTTPException(status_code=500, detail="서명된 URL 생성 실패")


@app.on_event("startup")
async def startup():
    print("DB연결완료")
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    print("DB연결해제")
    await database.disconnect()



build_path = os.path.join(os.path.dirname(__file__), "../build")






# 유저 접속 단


@app.get("/")
async def user():
    
    print("테스트2")
    return {"message": "테스트 완료"}

@app.get("/test")
async def user():
    print("테스트_코틀린")
    return "message : 코틀린 테스트 완료"

@app.get("/callback")
async def imgur_callback(request: Request):
    query_params = request.query_params
    authorization_code = query_params.get("code")
    if authorization_code:
        return {"message": "Authorization successful", "code": authorization_code}
    return {"message": "Authorization failed"}


@app.post("/user/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):  # 변수명을 login_data로 변경
    print("Logging in with:", login_data.user_id)

    # SQL 쿼리 작성
    sql = """
    SELECT user_id, user_pw, user_nickname FROM tb_user WHERE user_id = :user_id
    """
    
    # SQL 실행
    user = await database.fetch_one(sql, values={"user_id": login_data.user_id})

    if not user:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 잘못되었습니다.")
    
    try:
        # 입력된 비밀번호와 저장된 해싱된 비밀번호 비교
        ps.verify(user["user_pw"], login_data.user_pw)

        # 동적으로 role 설정 (관리자인지 사원인지)
        role = "사용자"

        # 응답에서 비밀번호를 제외한 정보만 반환
        return {
            "success": True,
            "message": "로그인 성공",
            "user": {
                "id": user["user_id"],
                "name": user["user_nickname"],
                "role": role,
            }
        }
    except exceptions.VerifyMismatchError:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 잘못되었습니다.")


@app.post("/user/join", response_model=JoinResponse)
async def join(join_data: JoinRequest):
    # print("join in with:", join_data.user_id)

    # Check if user_id or user_email already exists
    check_sql = """
    SELECT user_id FROM tb_user WHERE user_id = :user_id OR user_email = :user_email
    """
    existing_user = await database.fetch_one(check_sql, values={"user_id": join_data.user_id, "user_email": join_data.user_email})
    if existing_user:
        raise HTTPException(status_code=409, detail="이미 존재하는 아이디 또는 이메일입니다.") # 409 Conflict

    argon_join_pw = ps.hash(join_data.user_pw)

    
    # SQL 쿼리 작성 (해싱 제외)
    sql = """
    INSERT INTO tb_user(user_id, user_pw, user_nickname, user_email)
    VALUES (:user_id, :user_pw, :user_nickname, :user_email)
    """

    try:
        await database.execute(sql, values={
            "user_id": join_data.user_id,
            "user_pw": argon_join_pw,
            "user_nickname": join_data.user_nickname,
            "user_email": join_data.user_email
        })
        return JoinResponse(success=True, message=join_data.user_id) # success와 user_id를 함께 반환
    except Exception as e:
        print(f"데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="회원가입 중 오류가 발생했습니다.") # 500 Internal Server Error

