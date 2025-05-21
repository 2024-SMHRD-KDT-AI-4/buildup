from fastapi import APIRouter, HTTPException ,UploadFile, File
import boto3
import os
import logging
from typing import Annotated
# 수정된 임포트 (직접 임포트)
from schemas import (
    PresignedUrlRequest,
    PresignedUrlResponse,
    ImageUploadResponse
)
from dotenv import load_dotenv
load_dotenv()

router = APIRouter()
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
@router.post("/upload/image_base64", response_model=ImageUploadResponse)
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


@router.post("/get/presigned-url", response_model=PresignedUrlResponse)
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