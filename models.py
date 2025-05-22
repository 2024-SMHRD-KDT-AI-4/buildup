from sqlalchemy import JSON, Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.dialects.mysql import ENUM
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

# 데이터베이스 스키마 이름 설정
SCHEMA_NAME = "cgi_24K_AI4_p3_1"

# tb_user 모델 (사용자 정보 테이블)
class User(Base):
    __tablename__ = 'tb_user'
    __table_args__ = {'schema': SCHEMA_NAME}

    user_id = Column(String(50), primary_key=True)  # 기존에 PK로 사용한다 가정
    user_pw = Column(String(255), nullable=False)
    user_nickname = Column(String(50), nullable=False, index=True)  # MUL 인덱스 반영
    user_email = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # 관계 예시
    analyses = relationship("Analysis", back_populates="user")
    chatbot = relationship("Chatbot", back_populates="user")


# tb_analysis 모델 (분석 결과 테이블)
class Analysis(Base):
    __tablename__ = 'tb_analysis'
    __table_args__ = {'schema': SCHEMA_NAME}

    analysis_idx = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(50), ForeignKey(f"{SCHEMA_NAME}.tb_user.user_id"), nullable=False)
    analysis_model = Column(String(100), nullable=False)
    file_path = Column(String(1000), nullable=False)
    skin_tone = Column(String(50), nullable=False)
    personal_color = Column(String(50), nullable=False)
    analysis_result = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # User 테이블과 관계 설정 (필요시)
    user = relationship("User", back_populates="analyses")


# tb_chatbot 모델 (챗봇 대화 테이블)
class Chatbot(Base):
    __tablename__ = 'tb_chatbot'
    __table_args__ = {'schema': SCHEMA_NAME}  # 스키마 지정

    chatbot_idx = Column(Integer, primary_key=True, autoincrement=True)  # Primary Key
    user_id = Column(String(50), ForeignKey(f"{SCHEMA_NAME}.tb_user.user_id"), nullable=True)  # Foreign Key
    chatbot_role = Column(ENUM('나', '챗봇'), nullable=False)  # MySQL ENUM
    chatbot_text = Column(Text, nullable=True)  # Text column
    created_at = Column(DateTime, default=func.now(), nullable=True)  # Timestamp
    created_year = Column(Integer, nullable=True)  # Year
    created_month = Column(Integer, nullable=True)  # Month
    created_day = Column(Integer, nullable=True)  # Day

    # Relationship 설정 (Optional)
    user = relationship("User", back_populates="chatbot")  # User 테이블과 연결

class ChatGPT(Base):
    __tablename__ = 'tb_chatgpt'  # 테이블 이름 수정
    __table_args__ = {'schema': SCHEMA_NAME}  # 스키마 지정

    gpt_idx = Column(Integer, primary_key=True, autoincrement=True)  # Primary Key
    analysis_idx = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.tb_analysis.analysis_idx"), nullable=False)  # Foreign Key
    gpt_response = Column(Text, nullable=False)  # MediumText equivalent
    created_at = Column(DateTime, default=func.now(), nullable=False)  # Timestamp

    # Relationship 설정 (Optional)
    analysis = relationship("Analysis", back_populates="gpt_responses")  # Analysis 테이블과 연결   
