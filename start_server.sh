#!/bin/bash

# 프로젝트 디렉토리로 이동
cd /home/ec2-user/buildupBack || { 
    echo "Error: Directory /home/ec2-user/buildupBack not found."; 
    exit 1; 
}

# 가상 환경 활성화 (필요하면 사용)
# source /home/ec2-user/buildupBack/venv/bin/activate

# 현재 실행 중인 Uvicorn 프로세스 종료 (필요하면 사용)
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo "Stopping existing Uvicorn server..."
    pkill -f "uvicorn main:app"
fi

# Uvicorn 서버 실행
echo "Starting Uvicorn server..."
uvicorn main:app --host 127.0.0.1 --port 8000 --reload &

# 프로세스 ID 저장
SERVER_PID=$!
echo "Uvicorn server started with PID: $SERVER_PID"

# 종료 시그널 처리
trap "echo 'Stopping server...'; kill $SERVER_PID; exit 0" SIGINT SIGTERM

# 프로세스 대기
wait $SERVER_PID