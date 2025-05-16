from fastapi import FastAPI, HTTPException ,Request
from pydantic import BaseModel
from database import database  # database.py에서 인스턴스를 가져오기
from sqlalchemy import text
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

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

@app.on_event("startup")
async def startup():
    print("DB연결완료")
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    print("DB연결해제")
    await database.disconnect()



build_path = os.path.join(os.path.dirname(__file__), "../build")

# app.mount(
#     "/", 
#     StaticFiles(directory=os.path.abspath(build_path), html=True), 
#     name="static"
# )
# # React 빌드 파일 서빙
# app.mount("/", StaticFiles(directory="C:/Users/User/Desktop/buildup/build", html=True), name="static")



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
    SELECT tb_user.*, tb_admin.admin_id
    FROM tb_user
    LEFT JOIN tb_admin ON tb_user.user_id = tb_admin.user_id
    WHERE tb_user.user_id = :user_id AND tb_user.user_pw = :user_pw;
    """
    
    # SQL 실행
    result = await database.fetch_all(sql, values={"user_id": login_data.user_id, "user_pw": login_data.user_pw})

    if result:
        user = result[0]  # 첫 번째 사용자 정보
        
        # 동적으로 role 설정 (관리자인지 사원인지)
        role = "관리자" if user["admin_id"] else "사원"

        # 응답에서 비밀번호를 제외한 정보만 반환
        return {
            "success": True,
            "message": "로그인 성공",
            "user": {
                "id": user["user_id"],
                "name": user["user_nickname"],
                "role": role,
                "empID": ""
            }
        }
    else:
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 잘못되었습니다.")

@app.post("/user/join", response_model=JoinResponse)
async def join(join_data: JoinRequest):
    print("join in with:", join_data.user_id)

    # Check if user_id or user_email already exists
    check_sql = """
    SELECT user_id FROM tb_user WHERE user_id = :user_id OR user_email = :user_email
    """
    existing_user = await database.fetch_one(check_sql, values={"user_id": join_data.user_id, "user_email": join_data.user_email})
    if existing_user:
        raise HTTPException(status_code=409, detail="이미 존재하는 아이디 또는 이메일입니다.") # 409 Conflict

    # SQL 쿼리 작성 (해싱 제외)
    sql = """
    INSERT INTO tb_user(user_id, user_pw, user_nickname, user_email)
    VALUES (:user_id, :user_pw, :user_nickname, :user_email)
    """

    try:
        await database.execute(sql, values={
            "user_id": join_data.user_id,
            "user_pw": join_data.user_pw,
            "user_nickname": join_data.user_nickname,
            "user_email": join_data.user_email
        })
        return JoinResponse(success=True, message=join_data.user_id) # success와 user_id를 함께 반환
    except Exception as e:
        print(f"데이터베이스 오류 발생: {e}")
        raise HTTPException(status_code=500, detail="회원가입 중 오류가 발생했습니다.") # 500 Internal Server Error

