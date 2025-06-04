import logging
import argon2
from fastapi import APIRouter, HTTPException
#from routes.user import router as user_router  # routes 폴더에서 user.py의 router 가져오기
from database import database  # database.py에서 인스턴스를 가져오기
from sqlalchemy import text
from argon2 import PasswordHasher
from argon2 import exceptions
from argon2.exceptions import VerifyMismatchError
# from dotenv import load_dotenv
# load_dotenv()

from typing import Annotated
# 수정된 임포트 (직접 임포트)
from schemas import (
    JoinRequest,
    JoinResponse,
    LoginRequest,
    LoginResponse,
    ServerResponse,
    UpdateNicknameRequest,
    User,
    CheckIDRequest,
    CheckIDResponse,
    CheckPWRequest,
    CheckPWResponse,
    PastAnalysisRequest,
    PastAnalysisResponse,
    UpdatePWRequest,
    UpdatePWResponse
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
    SELECT * FROM tb_user WHERE user_id = :user_id
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
                email = user["user_email"],
                sex = user["user_sex"],
                birthdate= user["user_birthdate"],
                joinDate= user["created_at"],
                role=role
            )
        )
    except exceptions.VerifyMismatchError:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 잘못되었습니다.")


@router.post("/join", response_model=JoinResponse)
async def join(join_data: JoinRequest):
    print("join in with:", join_data)

    # Check if user_id or user_email already exists
    check_sql = """
    SELECT user_id FROM tb_user WHERE user_id = :user_id OR user_email = :user_email
    """
    existing_user = await database.fetch_one(check_sql, values={"user_id": join_data.user_id, "user_email": join_data.user_email})
    if existing_user:
        #raise HTTPException(status_code=409, detail="이미 존재하는 아이디 또는 이메일입니다.") # 409 Conflict
        return JoinResponse(success=False, message="이미 존재하는 아이디 또는 이메일입니다.(409)") # False와 user_id를 함께 반환

    argon_join_pw = ps.hash(join_data.user_pw)
    
    # SQL 쿼리 작성 (해싱 제외)
    sql = """
    INSERT INTO tb_user(user_id, user_pw, user_nickname, user_email, user_sex, user_birthdate)
    VALUES (:user_id, :user_pw, :user_nickname, :user_email, :user_sex, :user_birthdate)
    """

    try:
        print(f"데이터베이스 수정시도")
        await database.execute(sql, values={
            "user_id": join_data.user_id,
            "user_pw": argon_join_pw,
            "user_nickname": join_data.user_nickname,
            "user_email": join_data.user_email,
            "user_sex": join_data.user_sex,
            "user_birthdate": join_data.user_birthdate
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
        result = await database.fetch_one(check_sql, values={"user_id": check_data.user_id})

        if result is None:
            return CheckPWResponse(success=False, message="User not found.")

        stored_hashed_pw = result["user_pw"]

        try:
            # 비밀번호 검증
            ps.verify(stored_hashed_pw, check_data.user_pw)  # 순서 주의: verify(hashed, plain)
            return CheckPWResponse(success=True, message=check_data.user_id)
        except VerifyMismatchError:
            return CheckPWResponse(success=False, message="Invalid password.")

    except Exception as e:
        print(f"데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")
    
@router.post("/check-id", response_model=CheckIDResponse)
async def checkpw(check_data: CheckIDRequest):

    check_sql = """
    SELECT user_id FROM tb_user WHERE user_id = :user_id
    """
    try:
        result = await database.fetch_one(check_sql, values={"user_id": check_data.user_id})

        if result is None:
            return CheckIDResponse(success=True, possible=True, message="This ID can.")
        else:
            return CheckIDResponse(success=True, possible=False, message="This ID can`t.")

    except Exception as e:
        print(f"데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")



@router.post("/get/past-analysis", response_model=PastAnalysisResponse)
async def get_past_analysis(request_data: PastAnalysisRequest):
    user_id = request_data.user_id

    check_sql = """
    SELECT * FROM tb_analysis WHERE user_id = :user_id
    """

    try:
        # 여러 행을 가져오기 위해 fetch_all 사용
        results = await database.fetch_all(check_sql, values={"user_id": user_id})

        if not results:
            return PastAnalysisResponse(success=True, message="No records found", data=None)

        # JSON serializable 형태로 변환
        results_list = [dict(row) for row in results]

        return PastAnalysisResponse(
            success=True,
            message="Records retrieval successful",
            data=results_list
        )
    except Exception as e:
        logging.error(f"Database error while retrieving records for user_id={user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error occurred.")
    

@router.post("/update-pw", response_model=UpdatePWResponse)
async def checkpw(check_data: UpdatePWRequest):
    check_sql = "SELECT user_pw FROM tb_user WHERE user_id = :user_id"
    update_sql = "UPDATE tb_user SET user_pw = :user_pw WHERE user_id = :user_id"

    try:
        # 현재 비밀번호 확인
        result = await database.fetch_one(check_sql, values={"user_id": check_data.user_id})
        if result is None:
            return UpdatePWResponse(success=False, message="User not found.")

        stored_hashed_pw = result["user_pw"]
        # 비밀번호 검증 (hashed와 plain text의 순서를 정확히 유지)
        if not ps.verify(stored_hashed_pw, check_data.user_pw):
            return UpdatePWResponse(success=False, message="Password not matched.")

        # 새로운 비밀번호 해시화 및 업데이트
        hashed_new_pw = ps.hash(check_data.user_new_pw)
        await database.execute(update_sql, values={
            "user_id": check_data.user_id,
            "user_pw": hashed_new_pw,
        })

        return UpdatePWResponse(success=True, message="Password changed successfully.")

    except Exception as e:
        # 에러 로그 기록
        print(f"데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    
@router.post("/update-nickname", response_model=ServerResponse)
async def checkpw(check_data: UpdateNicknameRequest):

    update_sql = "UPDATE tb_user SET user_nickname = :user_nickname WHERE user_id = :user_id"

    try:

        # 새로운 비밀번호 해시화 및 업데이트
        await database.execute(update_sql, values={
            "user_id": check_data.user_id,
            "user_nickname": check_data.user_new_nickname
        })

        return ServerResponse(success=True, message="Nickname changed successfully.")

    except Exception as e:
        # 에러 로그 기록
        print(f"데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="An internal server error occurred.")