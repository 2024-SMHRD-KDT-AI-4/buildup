from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# 데이터베이스 스키마 이름 설정
SCHEMA_NAME = "cgi_24K_AI4_p3_1"

# tb_user 모델 (사용자 정보 테이블)
class User(Base):
    __tablename__ = 'tb_user'
    __table_args__ = {'schema': SCHEMA_NAME}  # 스키마 지정

    # 테이블의 컬럼 정의
    user_id = Column(String(50), primary_key=True)  # 기본 키
    user_pw = Column(String(60))  # 비밀번호
    user_nickname = Column(String(50))  # 사용자 닉네임
    user_email = Column(String(50))  # 사용자 이메일
    created_at = Column(DateTime, default=func.now())  # 레코드 생성 시 현재 시간 자동 기록

    # User와 관련된 Admin 객체를 불러올 때 관계 설정
    admin = relationship("Admin", back_populates="user", uselist=False)

# tb_admin 모델 (관리자 정보 테이블)
class Admin(Base):
    __tablename__ = 'tb_admin'
    __table_args__ = {'schema': SCHEMA_NAME}  # 스키마 지정

    # 테이블의 컬럼 정의
    admin_id = Column(Integer, primary_key=True)  # 기본 키
    user_id = Column(String(50), ForeignKey(f'{SCHEMA_NAME}.tb_user.user_id'))  # 외래 키 (사용자와 연결)
    created_at = Column(DateTime, default=func.now())  # 레코드 생성 시 현재 시간 자동 기록
    
    # Admin과 관련된 User 객체를 불러올 때 관계 설정
    user = relationship("User", back_populates="admin")
