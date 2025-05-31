from datetime import datetime
import sys
import tempfile
from fastapi import APIRouter, Form, HTTPException, UploadFile, File
import boto3
import os
import logging
from typing import Annotated
from typing import Dict, Any, List
from fastapi.responses import JSONResponse
import httpx # 현재 코드에서는 직접 사용되지 않지만, 기존에 포함되어 있었으므로 유지합니다.
import uuid
import pandas as pd

# sys.path.append 부분은 Poetry를 사용한다면 제거하는 것이 좋습니다.
# Poetry는 pyproject.toml에 정의된 경로를 자동으로 관리합니다.
sys.path.append(os.path.abspath("ShowMeTheColor/src"))
# SkinAnalysis 모듈 경로도 추가 (필요 시)
sys.path.append(os.path.abspath("SkinAnalysis"))


# 응답 및 요청 모델 정의 (FastAPI Pydantic) 임포트
from ShowMeTheColor.src.personal_color_analysis import personal_color
from schemas import (
    PresignedUrlRequest,
    PresignedUrlResponse,
    ImageUploadResponse
)
# SkinAnalysis 모듈에서 SkinAnalyzer 클래스 임포트 (이 부분이 수정되었습니다!)
from SkinAnalysis.aimodel import SkinAnalyzer

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


# 로깅 설정 (S3 서버에서도 필요)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# SkinAnalyzer 인스턴스를 전역적으로 생성 (서버 시작 시 한 번만 로드)
skin_analyzer_instance = None # 초기화 전 None으로 설정
try:
    # 모델 파일 경로를 SkinAnalysis 폴더 기준으로 정확하게 설정합니다.
    # 모델 파일이 'SkinAnalysis' 폴더 안에 있다고 가정합니다.
    # sys.path.append("SkinAnalysis") 가 설정되어 있다면, 이 경로는 SkinAnalysis 모듈 내부에서 처리됩니다.
    skin_analyzer_instance = SkinAnalyzer(
        model_save_path="image_to_measurement_model.pth",
        target_scaler_save_path="target_measurement_scaler.joblib",
        skin_type_model_filename="best_skin_type_model_v3_measurements_only.joblib",
        label_encoder_filename="label_encoder_v3_measurements_only.joblib"
    )
    logger.info("SkinAnalyzer 인스턴스 초기화 성공.")
except Exception as e:
    logger.error(f"SkinAnalyzer 인스턴스 초기화 실패: {e}. 피부 분석 서비스를 사용할 수 없습니다.", exc_info=True)
    skin_analyzer_instance = None # 로드 실패 시 None으로 설정


# API 엔드포인트: 이미지 업로드 및 분석 통합
@router.post("/upload-and-analyze", response_model=Dict[str, Any], summary="Upload image, save to S3, and analyze for personal color and skin")
async def upload_and_analyze_image(file: UploadFile = File(...), description: str = Form(...)):
    # 서비스 가용성 확인 (피부 분석 모델 로드 여부)
    if skin_analyzer_instance is None:
        logger.error("SkinAnalyzer instance was not initialized correctly. Skin analysis service is unavailable.")
        raise HTTPException(
            status_code=503,
            detail="Skin analysis service is currently unavailable due to a server configuration issue. Please check server logs."
        )

    try:
        contents = await file.read()
        # 현재 시간을 ISO 8601 형식으로 생성
        db_timestamp = datetime.now()

        # 파일 이름에 사용할 간결한 시간 포맷
        currentTime = db_timestamp.strftime('%y%m%dT%H%M%S')
        # 파일 확장자 추출
        file_extension = os.path.splitext(file.filename)[1]
        # 파일 이름에 UUID와 원본 파일명을 조합하여 고유성 강화
        file_name = f"{currentTime}_{uuid.uuid4()}{file_extension}"

        s3_key = f"images/{file_name}"
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=contents,
            ContentType=file.content_type # S3에 Content-Type 메타데이터 추가
        )
        s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
        logger.info(f"File uploaded to S3: {s3_url}")

        # Personal Color 분석을 위한 로컬 임시 파일 생성
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(contents)
            temp_filepath = temp_file.name
        logger.info(f"Temporary file created for personal color analysis: {temp_filepath}")

        # 1. Personal Color Analysis
        analysis_result_tone = None
        try:
            analysis_result_tone = personal_color.analysis(temp_filepath)
            logger.info(f"Personal color analysis completed. Result: {analysis_result_tone}")
        except Exception as e:
            logging.error(f"Personal color analysis failed: {e}", exc_info=True)
            # 실패하더라도 HTTP 500 대신, 응답에 실패 메시지를 포함
            analysis_result_tone = {"error": "Personal color analysis failed"}
        finally:
            # 임시 파일 반드시 삭제
            if os.path.exists(temp_filepath):
                os.unlink(temp_filepath)
                logger.info(f"Temporary file {temp_filepath} deleted.")

        # 2. Skin Analysis (S3 URL 사용) - analysis_result_tone 바로 다음에 위치
        skin_analysis_results = {"average_measurements": {}, "predicted_skin_type": "분석 실패"} # 기본값
        try:
            # SkinAnalyzer의 analyze_s3_images_for_person은 URL 리스트를 받으므로, 단일 URL을 리스트로 감싸서 전달
            skin_analysis_raw_results = skin_analyzer_instance.analyze_s3_images_for_person([s3_url])

            if "error" in skin_analysis_raw_results:
                logger.error(f"S3 이미지 피부 분석 중 오류 발생: {skin_analysis_raw_results['error']}")
                skin_analysis_results["predicted_skin_type"] = f"피부 분석 오류: {skin_analysis_raw_results['error']}"
            else:
                skin_analysis_results["average_measurements"] = skin_analysis_raw_results.get("average_measurements", {})
                skin_analysis_results["predicted_skin_type"] = skin_analysis_raw_results.get("predicted_skin_type", "분석 성공")
            logger.info(f"Skin analysis completed. Predicted Skin Type: {skin_analysis_results['predicted_skin_type']}.")

        except (ValueError, RuntimeError) as e:
            logger.error(f"Skin analysis using S3 URL failed for {s3_url}: {e}", exc_info=True)
            skin_analysis_results["predicted_skin_type"] = f"피부 분석 실패: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error during skin analysis for {s3_url}: {e}", exc_info=True)
            skin_analysis_results["predicted_skin_type"] = "피부 분석 중 예상치 못한 오류 발생"

        return JSONResponse(content={
            "success": True,
            "message": "Image uploaded and analyzed successfully.",
            "s3_url": s3_url,
            "created_at": currentTime,
            "personal_color_tone": analysis_result_tone,
            "skin_analysis": skin_analysis_results, # 피부 분석 결과 추가
            "db_timestamp": db_timestamp.isoformat(),
            "requester":description
        })

    except Exception as e:
        logging.error(f"Error during upload and analyze: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Error occurred during upload and analyze process.")

# 이미지 업로드 API 엔드포인트 정의 (기존 코드 유지)
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