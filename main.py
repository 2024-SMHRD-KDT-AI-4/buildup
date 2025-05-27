from fastapi import FastAPI, HTTPException ,Request
from routes.user import router as user_router  # routes 폴더에서 user.py의 router 가져오기
from routes.upload import router as upload_router  # routes 폴더에서 user.py의 router 가져오기
from routes.chatbot import router as chatbot_router  # routes 폴더에서 user.py의 router 가져오기
from routes.analysis import router as analysis_router  # routes 폴더에서 user.py의 router 가져오기
from routes.analysis import router as analysis_router  # routes 폴더에서 user.py의 router 가져오기
from database import database  # database.py에서 인스턴스를 가져오기
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

import os
# 로깅 설정
import logging



# 기본 로깅 레벨을 WARNING으로 설정
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.WARNING)



# FastAPI 인스턴스 생성
app = FastAPI()
# 라우터 등록
app.include_router(user_router, prefix="/user")
app.include_router(upload_router, prefix="/images")
app.include_router(chatbot_router, prefix="/chatbot")
app.include_router(analysis_router, prefix="/analysis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 도메인 허용. 필요시 특정 도메인으로 제한.
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드 허용.
    allow_headers=["*"],  # 모든 헤더 허용.
)

@app.on_event("startup")
async def startup():
    print("Server startup - Initializing resources")
    print("DB연결완료")
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    print("DB연결해제")
    print("Server shutdown - Cleaning up resources")
    await database.disconnect()


build_path = os.path.join(os.path.dirname(__file__), "../build")


@app.get("/")
async def root():
    print("서버 가동 중")
    return {"message": "Welcome to FastAPI!"}

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
