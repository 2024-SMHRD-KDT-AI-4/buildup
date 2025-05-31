import torch
import torch.nn as nn
from torchvision import transforms
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights
from PIL import Image
import numpy as np
import pandas as pd
import os
import joblib
import logging
from typing import List, Dict, Any
# import io # 이제 S3 직접 로딩 안 하므로 필요 없음
# import boto3 # 이제 S3 직접 로딩 안 하므로 필요 없음

logger = logging.getLogger(__name__)

# --- 1. 피부 측정값 예측 모델 (Torch) 정의 ---
class ImageToMeasurementModel(nn.Module):
    def __init__(self, num_output_measurements):
        super().__init__()
        weights = EfficientNet_B0_Weights.IMAGENET1K_V1
        self.backbone = efficientnet_b0(weights=weights)
        num_ftrs = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Identity()
        self.regression_head = nn.Sequential(
            nn.Linear(num_ftrs, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_output_measurements)
        )
    def forward(self, x):
        x = self.backbone(x)
        x = self.regression_head(x)
        return x
    def freeze_backbone(self):
        for param in self.backbone.parameters():
            param.requires_grad = False
    def unfreeze_backbone(self):
        for param in self.backbone.parameters():
            param.requires_grad = True

# --- 2. 피부 분석을 위한 메인 클래스 정의 ---
class SkinAnalyzer:
    def __init__(self,
                 model_save_path: str = "image_to_measurement_model.pth",
                 target_scaler_save_path: str = "target_measurement_scaler.joblib",
                 skin_type_model_filename: str = 'best_skin_type_model_v3_measurements_only.joblib',
                 label_encoder_filename: str = 'label_encoder_v3_measurements_only.joblib',
                 device: str = None):
        
        # 현재 파일(aimodel.py)이 위치한 디렉토리의 절대 경로를 얻어 모델 파일 경로의 기준점으로 삼습니다.
        self.base_dir = os.path.dirname(os.path.abspath(__file__)) 

        self.IMG_HEIGHT = 256
        self.IMG_WIDTH = 256
        self.DEVICE = torch.device(device if device else ("cuda" if torch.cuda.is_available() else "cpu"))

        self.SELECTED_MEASUREMENT_COLS = [
            '수분_이마', '수분_오른쪽볼', '수분_왼쪽볼', '수분_턱',
            '탄력_턱_R2', '탄력_왼쪽볼_R2', '탄력_오른쪽볼_R2', '탄력_이마_R2',
            '모공개수_오른쪽볼', '모공개수_왼쪽볼',
            '스팟개수_정면',
            '주름_왼쪽눈가_Ra', '주름_왼쪽눈가_Rmax',
            '주름_오른쪽눈가_Ra', '주름_오른쪽눈가_Rmax'
        ]
        self.NUM_TARGET_MEASUREMENTS = len(self.SELECTED_MEASUREMENT_COLS)

        # 각 모델 파일 경로를 절대 경로로 재정의합니다.
        self.model_save_path = os.path.join(self.base_dir, model_save_path)
        self.target_scaler_save_path = os.path.join(self.base_dir, target_scaler_save_path)
        self.skin_type_model_filename = os.path.join(self.base_dir, skin_type_model_filename)
        self.label_encoder_filename = os.path.join(self.base_dir, label_encoder_filename)

        self.model_to_predict = None
        self.target_scaler = None
        self.skin_type_model_pipeline = None
        self.label_encoder = None

        # S3 클라이언트 초기화 코드 제거 (SkinAnalyzer가 S3 직접 접근 안 함)
        # self.s3_client = boto3.client(...)

        self._load_models() # 객체 생성 시 모델들을 로드

        # 검증 데이터용 이미지 변환 (학습 때와 동일한 val_transform 사용)
        normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        self.val_transform = transforms.Compose([
            transforms.Resize((self.IMG_HEIGHT, self.IMG_WIDTH)),
            transforms.ToTensor(),
            normalize
        ])

    def _load_models(self):
        """
        초기화 시 모든 필요한 모델과 스케일러를 로드합니다.
        """
        logger.info(f"Loading ImageToMeasurementModel from: {self.model_save_path}")
        try:
            self.model_to_predict = ImageToMeasurementModel(num_output_measurements=self.NUM_TARGET_MEASUREMENTS)
            if not os.path.exists(self.model_save_path):
                raise FileNotFoundError(f"모델 파일({self.model_save_path})을 찾을 수 없습니다.")
            self.model_to_predict.load_state_dict(torch.load(self.model_save_path, map_location=self.DEVICE))
            self.model_to_predict.to(self.DEVICE)
            self.model_to_predict.eval()
            logger.info(f"모델 로드 완료: {self.model_save_path}")
        except FileNotFoundError as e:
            logger.error(f"오류: {e}")
            self.model_to_predict = None
        except Exception as e:
            logger.error(f"ImageToMeasurementModel 로드 중 예상치 못한 오류 발생: {e}", exc_info=True)
            self.model_to_predict = None

        logger.info(f"Loading Target Scaler from: {self.target_scaler_save_path}")
        if os.path.exists(self.target_scaler_save_path):
            self.target_scaler = joblib.load(self.target_scaler_save_path)
            logger.info(f"타겟 스케일러 로드 완료: {self.target_scaler_save_path}")
        else:
            logger.warning(f"경고: 타겟 스케일러 파일({self.target_scaler_save_path})을 찾을 수 없습니다. 원래 스케일 변환 불가.")

        logger.info(f"Loading Skin Type Prediction Model and Label Encoder from: {self.skin_type_model_filename} and {self.label_encoder_filename}")
        try:
            if not os.path.exists(self.skin_type_model_filename):
                raise FileNotFoundError(f"피부 타입 예측 모델 파일({self.skin_type_model_filename})을 찾을 수 없습니다.")
            self.skin_type_model_pipeline = joblib.load(self.skin_type_model_filename)
            logger.info(f"'{self.skin_type_model_filename}'에서 피부 타입 예측 모델(파이프라인) 로드 완료.")
            
            if not os.path.exists(self.label_encoder_filename):
                raise FileNotFoundError(f"레이블 인코더 파일({self.label_encoder_filename})을 찾을 수 없습니다.")
            self.label_encoder = joblib.load(self.label_encoder_filename)
            logger.info(f"'{self.label_encoder_filename}'에서 레이블 인코더 로드 완료.")
            
        except FileNotFoundError as fnfe:
            logger.error(f"오류: 필요한 모델 또는 인코더 파일({fnfe.filename})을 찾을 수 없습니다. 피부 타입 예측 모델 학습 및 저장 스크립트를 먼저 실행했는지 확인하세요.")
            self.skin_type_model_pipeline = None
            self.label_encoder = None
        except Exception as e:
            logger.error(f"피부 타입 예측 모델 또는 객체 로드 중 오류 발생: {e}", exc_info=True)
            self.skin_type_model_pipeline = None
            self.label_encoder = None

    def _preprocess_image(self, image: Image.Image):
        """이미지를 모델 입력에 맞게 전처리합니다."""
        return self.val_transform(image)

    # 이 메서드는 로컬 파일 경로를 받아서 피부 측정값을 예측합니다.
    def predict_measurements_from_local_path(self, image_path: str) -> np.ndarray:
        """
        단일 로컬 이미지 경로를 받아 피부 측정값을 예측합니다.
        반환값은 원래 스케일로 변환된 numpy 배열입니다.
        """
        if self.model_to_predict is None:
            raise RuntimeError("이미지 측정값 예측 모델이 로드되지 않았습니다.")

        try:
            input_image_pil = Image.open(image_path).convert('RGB')
        except Exception as e:
            logger.error(f"이미지를 여는 중 문제 발생 ({image_path}): {e}")
            raise ValueError(f"이미지 파일 '{image_path}'을(를) 읽을 수 없습니다.")

        input_tensor = self._preprocess_image(input_image_pil) # _preprocess_image 재활용
        input_batch = input_tensor.unsqueeze(0).to(self.DEVICE)

        with torch.no_grad():
            scaled_predictions = self.model_to_predict(input_batch)
        scaled_predictions_np = scaled_predictions.cpu().numpy().flatten()

        if self.target_scaler:
            original_scale_predictions = self.target_scaler.inverse_transform(scaled_predictions_np.reshape(1, -1)).flatten()
            return original_scale_predictions
        else:
            logger.warning("타겟 스케일러가 없어 스케일링된 측정값을 반환합니다.")
            return scaled_predictions_np

    # 이 메서드가 FastAPI 엔드포인트에서 호출될 메인 함수입니다.
    # 이제 로컬 파일 경로(temp_filepath)를 받습니다.
    def analyze_skin_from_local_path(self, local_image_path: str) -> Dict[str, Any]:
        """
        단일 로컬 이미지 경로를 받아 피부 분석을 수행합니다.
        """
        if not all([self.model_to_predict, self.target_scaler, self.skin_type_model_pipeline, self.label_encoder]):
            logger.error("피부 분석 모델이 완전히 로드되지 않아 분석을 수행할 수 없습니다.")
            return {"error": "피부 분석 모델이 완전히 로드되지 않았습니다. 서버 로그를 확인하세요."}
        
        all_measurements = []
        logger.info(f"로컬 이미지 처리 중: {local_image_path}")
        try:
            measurements = self.predict_measurements_from_local_path(local_image_path)
            all_measurements.append(measurements)
        except (ValueError, RuntimeError) as e:
            logger.warning(f"로컬 이미지 '{local_image_path}' 처리 중 오류 발생: {e}. 분석을 중단합니다.")
            return {"error": f"로컬 이미지 분석 실패: {str(e)}"}

        if not all_measurements:
            logger.warning(f"제공된 로컬 경로에서 처리 가능한 이미지가 없거나 예측에 실패했습니다.")
            return {"error": "No processable images found or prediction failed from local path."}

        # 단일 이미지이므로 평균 계산은 단순화됩니다.
        average_predictions = np.array(all_measurements).flatten()
        
        # 이렇게 수정합니다:
        avg_pred_dict = {self.SELECTED_MEASUREMENT_COLS[i]: float(round(average_predictions[i], 2)) for i in range(len(self.SELECTED_MEASUREMENT_COLS))}
        # avg_pred_dict = {self.SELECTED_MEASUREMENT_COLS[i]: round(average_predictions[i], 2) for i in range(len(self.SELECTED_MEASUREMENT_COLS))}
        avg_pred_df = pd.DataFrame([avg_pred_dict])

        logger.info(f"\n--- 로컬 이미지({os.path.basename(local_image_path)})에 대한 종합 예측 결과 ---")
        for col_name, value in avg_pred_dict.items():
            logger.info(f"{col_name}: {value:.2f}")
        
        predicted_skin_type = "예측 불가"
        if self.skin_type_model_pipeline and self.label_encoder:
            try:
                input_for_prediction = avg_pred_df[self.SELECTED_MEASUREMENT_COLS]
                numerical_predictions = self.skin_type_model_pipeline.predict(input_for_prediction)
                text_predictions = self.label_encoder.inverse_transform(numerical_predictions)
                predicted_skin_type = text_predictions[0]
                
                logger.info(f"\n--- 최종 피부 타입 예측 결과 ---")
                logger.info(f"예측 피부타입: {predicted_skin_type} (인코딩된 값: {numerical_predictions[0]})")
                
            except Exception as e:
                logger.error(f"피부 타입 예측 중 오류 발생: {e}", exc_info=True)
                predicted_skin_type = "예측 오류"
        else:
            logger.warning("피부 타입 예측 모델 또는 레이블 인코더 로드에 실패하여 피부 타입 예측을 수행할 수 없습니다.")
        
        return {
            "average_measurements": avg_pred_dict,
            "predicted_skin_type": predicted_skin_type,
            "measurement_columns": self.SELECTED_MEASUREMENT_COLS
        }