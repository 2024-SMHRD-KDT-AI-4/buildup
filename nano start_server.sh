#!/bin/bash

# Navigate to project directory
cd /home/ec2-user/buildupBack || exit

# Activate virtual environment (필요하면 추가)
# source /home/ec2-user/buildupBack/venv/bin/activate

# Start Uvicorn server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload