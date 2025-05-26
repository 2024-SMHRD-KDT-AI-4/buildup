import os
import shutil
import tempfile
import sys
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
import logging

sys.path.append(os.path.abspath("ShowMeTheColor/src"))

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 응답 및 요청 모델 정의 (FastAPI Pydantic) 임포트
from ShowMeTheColor.src.personal_color_analysis import personal_color

from schemas import (
    AnalyzeS3ImageRequest,
    AnalyzeS3ImageResponse,
)

# FastAPI 애플리케이션 인스턴스 생성
router = APIRouter()

# 유틸리티 함수: 이미지 파일 유효성 검사
def is_image_file(filename: str) -> bool:
    """주어진 파일 이름이 일반적인 이미지 확장자를 가지는지 확인합니다."""
    return filename.lower().endswith(('.png', '.jpg', '.jpeg'))

# API 엔드포인트: 단일 이미지 분석
@router.post("/singleimage/", summary="Analyze a single image for personal color")
async def analyze_single_image(
    file: UploadFile = File(..., description="The image file to analyze (PNG, JPG, JPEG).")
) -> Dict[str, Any]:
    """
    **단일 이미지**를 업로드하여 퍼스널 컬러 분석을 수행합니다.

    - **file**: 업로드할 이미지 파일. 지원되는 형식: PNG, JPG, JPEG.
    """
    if personal_color is None:
        logger.error("Personal color module was not loaded correctly at server startup. Service is unavailable.")
        raise HTTPException(
            status_code=503,
            detail="Personal color analysis service is currently unavailable due to a server configuration issue. Please check server logs."
        )

    logger.info(f"Received request for image analysis: {file.filename}")

    # 파일 유형 검사
    if not is_image_file(file.filename):
        logger.warning(f"Invalid file type uploaded: {file.filename}. Rejecting request.")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type for '{file.filename}'. Only PNG, JPG, JPEG files are allowed."
        )

    # 임시 디렉토리에 파일 저장
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_filepath = os.path.join(tmp_dir, file.filename)
        logger.info(f"Saving uploaded file temporarily to: {temp_filepath}")

        try:
            # 업로드된 파일의 내용을 비동기적으로 읽어 임시 파일에 씁니다.
            with open(temp_filepath, "wb") as buffer:
                while True:
                    chunk = await file.read(1024 * 1024)  # 1MB 청크
                    if not chunk:
                        break
                    buffer.write(chunk)
            
            logger.info(f"File '{file.filename}' saved successfully. Calling personal color analysis function.")
            
            # personal_color.analysis 함수로부터 결과를 받습니다.
            analysis_result_tone = personal_color.analysis(temp_filepath)
            
            logger.info(f"Analysis process completed for '{file.filename}'. Result: {analysis_result_tone}.")
            
            # JSON 응답 반환
            return JSONResponse(content={
                "message": "Image analysis successful.",
                "filename": file.filename,
                "personal_color_tone": analysis_result_tone,
                "note": "The detailed result is now directly included in this JSON response."
            })

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing image '{file.filename}': {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error occurred while processing image '{file.filename}': {e}. Please check server logs."
            )
