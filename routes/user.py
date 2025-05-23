import argon2
from fastapi import APIRouter, HTTPException
#from routes.user import router as user_router  # routes 폴더에서 user.py의 router 가져오기
from database import database  # database.py에서 인스턴스를 가져오기
from sqlalchemy import text
from argon2 import PasswordHasher
from argon2 import exceptions
# from dotenv import load_dotenv
# load_dotenv()

from typing import Annotated
# 수정된 임포트 (직접 임포트)
from schemas import (
    JoinRequest,
    JoinResponse,
    LoginRequest,
    LoginResponse,
    User,
    CheckPWRequest,
    CheckPWResponse
)


router = APIRouter()

# 비밀번호 해시와 검증 기능을 수행하는 객체를 생성
ps = PasswordHasher()
# 유저 접속 단

@router.post("/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
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
        role = "사용자"  # 실제 로직에 따라 "관리자"로 설정 가능

        # LoginResponse에 맞게 반환
        return LoginResponse(
            success=True,
            message="로그인 성공",
            user=User(
                id=user["user_id"],
                nickname=user["user_nickname"],
                role=role
            )
        )
    except exceptions.VerifyMismatchError:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 잘못되었습니다.")


@router.post("/join", response_model=JoinResponse)
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
    

@router.post("/check-pw", response_model=CheckPWResponse)
async def checkpw(check_data: CheckPWRequest):


    check_sql = """
    SELECT user_pw FROM tb_user WHERE user_id = :user_id
    """
    try:
        # 데이터베이스에서 해시된 비밀번호 가져오기
        result = await database.fetch_one(check_sql, values={"user_id": check_data.user_id})

        if result is None:
            return CheckPWResponse(success=False, message="User not found.")  # 사용자 없음
        
        stored_hashed_pw = result["user_pw"]

        # 입력 비밀번호와 저장된 해시 비교
        if ps.verify(check_data.user_pw, stored_hashed_pw):
            return CheckPWResponse(success=True, message=check_data.user_id)  # 비밀번호 일치
        else:
            return CheckPWResponse(success=False, message="Invalid password.")  # 비밀번호 불일치

    except Exception as e:
        print(f"데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="회원가입 중 오류가 발생했습니다.") # 500 Internal Server Error



