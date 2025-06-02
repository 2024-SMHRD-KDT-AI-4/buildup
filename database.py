from databases import Database

# 데이터베이스 연결 설정을 위한 변수들
DB_USER = "cgi_24K_AI4_p3_1"  # MySQL 사용자
DB_PASSWORD = "smhrd1"  # MySQL 비밀번호
DB_HOST = "project-db-cgi.smhrd.com"  # MySQL 호스트 (localhost)
DB_PORT = "3307"  # MySQL 포트 (기본 3306)
DB_NAME = "cgi_24K_AI4_p3_1"  # 데이터베이스 이름
	
# MySQL 연결 URI 포맷 (databases 라이브러리용)
DATABASE_URL = f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 비동기 데이터베이스 객체 생성
database = Database(DATABASE_URL)