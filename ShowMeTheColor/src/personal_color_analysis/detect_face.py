# coding: utf-8
# import the necessary packages
import os # 파일 상단에 이 줄을 추가합니다.
from imutils import face_utils
import numpy as np
import dlib
import cv2
# import matplotlib.pyplot as plt # 현재 코드에서 사용되지 않으므로 주석 처리 가능

class DetectFace:
    def __init__(self, image_path): # 매개변수 이름을 image_path로 변경하여 명확성 향상
        # initialize dlib's face detector (HOG-based)
        # and then create the facial landmark predictor
        self.detector = dlib.get_frontal_face_detector()

        # 현재 파일(detect_face.py)이 있는 디렉토리의 절대 경로를 얻습니다.
        current_file_dir = os.path.dirname(os.path.abspath(__file__))

        # current_file_dir (personal_color_analysis)에서부터 dat 파일까지의 상대 경로를 계산합니다.
        # personal_color_analysis/ -> src/ (../) -> ShowMeTheColor/ (../) -> res/ (res/) -> dat_file
        dat_file_path = os.path.join(current_file_dir, '../../res/shape_predictor_68_face_landmarks.dat')

        # 최종적으로 생성된 경로를 사용하여 파일을 엽니다.

        # !!! 중요: 이 파일 경로가 실제 .dat 파일 위치와 일치하는지 반드시 확인하세요. !!!
        # 예: ShowMeTheColor 폴더 밑에 res 폴더를 만들고 그 안에 .dat 파일을 넣으세요.
        try:
            self.predictor = dlib.shape_predictor(dat_file_path)
            #self.predictor = dlib.shape_predictor('../../res/shape_predictor_68_face_landmarks.dat')
        except RuntimeError as e:
            print(f"Error loading shape_predictor: {e}")
            print("'.dat' 파일 경로를 확인해주세요. 'ShowMeTheColor/res/' 폴더에 파일이 있는지 확인하세요.")
            # 여기서 프로그램을 종료하거나, 적절한 예외 처리를 할 수 있습니다.
            raise  # 혹은 return 이나 다른 방식으로 __init__ 실패를 알림

        # face detection part
        self.img = cv2.imread(image_path)
        if self.img is None: # 이미지 로드 실패 시 처리
            print(f"Error: 이미지를 로드할 수 없습니다. 경로를 확인하세요: {image_path}")
            # 얼굴 부위 변수들을 빈 값으로 초기화하고 반환할 수 있도록 __init__에서 값 반환 X
            self.right_eyebrow = []
            self.left_eyebrow = []
            self.right_eye = []
            self.left_eye = []
            self.left_cheek = []
            self.right_cheek = []
            self.face_detected = False # 얼굴 검출 실패 플래그
            return

        # if self.img.shape[0]>500:
        #     self.img = cv2.resize(self.img, dsize=(0,0), fx=0.8, fy=0.8)

        # init face parts
        self.right_eyebrow = []
        self.left_eyebrow = []
        self.right_eye = []
        self.left_eye = []
        self.left_cheek = []
        self.right_cheek = []
        self.face_detected = True # 기본적으로 얼굴 검출 성공으로 가정

        # detect the face parts and set the variables
        self.detect_face_part()

    # return type : np.array
    def detect_face_part(self):
        if not self.face_detected: # __init__에서 이미지 로드 실패 시
            return

        gray_img = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        rects = self.detector(gray_img, 1)

        # !!! 중요: 얼굴 검출 실패 시 처리 !!!
        if len(rects) == 0:
            print("경고: 이미지에서 얼굴을 찾을 수 없습니다.")
            self.face_detected = False # 얼굴 검출 실패 플래그 설정
            # 얼굴 부위 변수들은 이미 __init__에서 빈 리스트로 초기화되어 있음
            return # 여기서 함수 종료

        # 첫 번째 검출된 얼굴 사용 (여러 얼굴이 있을 경우, 필요에 따라 로직 수정 가능)
        rect = rects[0]

        face_parts = [[],[],[],[],[],[],[]] # 길이 7의 리스트로 초기화 (FACIAL_LANDMARKS_IDXS 항목 수에 맞게)
        num_face_landmark_groups = len(face_utils.FACIAL_LANDMARKS_IDXS)
        face_parts = [[] for _ in range(num_face_landmark_groups)]
        # determine the facial landmarks for the face region, then
        # convert the landmark (x, y)-coordinates to a NumPy array
        try:
            shape = self.predictor(gray_img, rect)
            shape = face_utils.shape_to_np(shape) # shape은 (68, 2) 형태의 배열이 됨
        except Exception as e: # 랜드마크 예측 실패 시
            print(f"랜드마크 예측 중 오류 발생: {e}")
            self.face_detected = False
            return

        # shape 배열의 실제 크기가 68인지 확인 (일반적으로 68개 랜드마크)
        if shape.shape[0] != 68:
            print(f"경고: 예상된 68개의 랜드마크를 찾지 못했습니다. (찾은 개수: {shape.shape[0]})")
            self.face_detected = False
            return

        idx = 0
        # loop over the face parts individually
        # imutils.face_utils.FACIAL_LANDMARKS_IDXS 는 일반적으로 7개의 주요 부위를 가짐
        # (mouth, right_eyebrow, left_eyebrow, right_eye, left_eye, nose, jaw)
        # 순서와 개수를 확인하려면 print(list(face_utils.FACIAL_LANDMARKS_IDXS.keys())) 등으로 확인
        expected_num_face_parts = len(face_utils.FACIAL_LANDMARKS_IDXS)
        #if len(face_parts) < expected_num_face_parts:
        #    print(f"경고: face_parts 리스트의 길이가 FACIAL_LANDMARKS_IDXS 항목 수({expected_num_face_parts})보다 작습니다.")
            # 필요시 face_parts 크기 동적 조절 또는 오류 처리
        #    self.face_detected = False
        #    return

        for (name, (i, j)) in face_utils.FACIAL_LANDMARKS_IDXS.items():
            # i, j 인덱스가 shape 배열의 범위를 벗어나지 않는지 확인
            if i < 0 or j > shape.shape[0] or i >= j:
                print(f"오류: '{name}' 부위의 랜드마크 인덱스(i={i}, j={j})가 잘못되었습니다. shape 범위: (0, {shape.shape[0]-1})")
                face_parts[idx] = np.array([]) # 빈 배열로 설정 또는 오류 처리
            else:
                face_parts[idx] = shape[i:j]
            idx += 1
        
        # face_parts 슬라이싱: [1:5]는 right_eyebrow, left_eyebrow, right_eye, left_eye에 해당
        # 이 슬라이싱이 FACIAL_LANDMARKS_IDXS의 실제 순서와 의도에 맞는지 확인 필요
        # 예를 들어, FACIAL_LANDMARKS_IDXS.items()의 순서가
        # 0: mouth, 1: right_eyebrow, 2: left_eyebrow, 3: right_eye, 4: left_eye, 5: nose, 6: jaw 라면
        # face_parts[1:5]는 실제로는 right_eyebrow, left_eyebrow, right_eye, left_eye를 가져옴
        # 이 부분의 인덱싱은 imutils.face_utils.FACIAL_LANDMARKS_IDXS의 내부 순서에 매우 의존적임.
        # 더 안전한 방법은 name을 기준으로 필요한 부분을 가져오는 것임.
        
        # 필요한 부위만 이름으로 찾아서 할당하는 방식 (더 안정적)
        landmark_dict = {}
        temp_idx = 0
        for (name, (i,j)) in face_utils.FACIAL_LANDMARKS_IDXS.items():
            if i < 0 or j > shape.shape[0] or i >=j: # 위와 동일한 인덱스 유효성 검사
                 landmark_dict[name] = np.array([])
            else:
                 landmark_dict[name] = shape[i:j]
            temp_idx +=1

        # 필요한 부위들을 명시적으로 할당
        self.right_eyebrow = self.extract_face_part(landmark_dict.get("right_eyebrow", np.array([])))
        self.left_eyebrow = self.extract_face_part(landmark_dict.get("left_eyebrow", np.array([])))
        self.right_eye = self.extract_face_part(landmark_dict.get("right_eye", np.array([])))
        self.left_eye = self.extract_face_part(landmark_dict.get("left_eye", np.array([])))

        # Cheeks are detected by relative position to the face landmarks
        # 이 부분도 shape의 특정 인덱스에 의존하므로, 랜드마크 검출 실패 시 오류 발생 가능
        try:
            # 랜드마크 인덱스가 shape 배열의 범위를 벗어나지 않는지 확인
            if all(idx < shape.shape[0] for idx in [29, 33, 4, 48, 54, 12]):
                # y 좌표 슬라이싱 시 y1 < y2 인지, x 좌표 슬라이싱 시 x1 < x2 인지 확인 필요
                y1_cheek, y2_cheek = shape[29][1], shape[33][1]
                x1_left_cheek, x2_left_cheek = shape[4][0], shape[48][0]
                x1_right_cheek, x2_right_cheek = shape[54][0], shape[12][0] # 주의: shape[12][0]이 shape[54][0] 보다 작을 수 있음

                if y1_cheek < y2_cheek:
                    if x1_left_cheek < x2_left_cheek :
                        self.left_cheek = self.img[y1_cheek:y2_cheek, x1_left_cheek:x2_left_cheek]
                    if x1_right_cheek > x2_right_cheek : # 일반적인 경우 x1 < x2 이지만, 코드상 반대이므로 수정
                        self.right_cheek = self.img[y1_cheek:y2_cheek, x2_right_cheek:x1_right_cheek] # 순서 변경
                    elif x1_right_cheek < x2_right_cheek : # 만약 이 경우가 맞다면
                        self.right_cheek = self.img[y1_cheek:y2_cheek, x1_right_cheek:x2_right_cheek]

            else:
                print("경고: 뺨 계산을 위한 랜드마크 인덱스가 범위를 벗어났습니다.")
        except IndexError:
            print("경고: 뺨 영역 계산 중 IndexError 발생.")
            # self.left_cheek, self.right_cheek은 이미 [] 로 초기화 되어 있음

    # parameter example : self.right_eye
    # return type : image
    def extract_face_part(self, face_part_points):
        if face_part_points is None or len(face_part_points) == 0: # 입력이 비었는지 확인
            return np.array([]) # 빈 배열 반환

        (x, y, w, h) = cv2.boundingRect(face_part_points)
        
        # boundingRect가 비정상적인 값을 반환하는 경우 방지 (w=0 또는 h=0)
        if w == 0 or h == 0:
            return np.array([])

        crop = self.img[y:y+h, x:x+w]
        
        # crop이 성공적으로 되었는지 확인 (간혹 boundingRect 결과로 crop이 안될 수 있음)
        if crop.size == 0:
            return np.array([])

        adj_points = np.array([np.array([p[0]-x, p[1]-y]) for p in face_part_points])

        # Create an mask
        mask = np.zeros((crop.shape[0], crop.shape[1]))
        cv2.fillConvexPoly(mask, adj_points, 1) # adj_points가 유효한 convex polygon을 형성해야 함
        mask = mask.astype(bool) # np.bool 대신 bool 사용 (최신 numpy 권장)
        
        # crop과 mask의 차원이 같은지 확인 (색상 채널 유무에 따라 다를 수 있음)
        # 현재 crop은 BGR이므로 마스크를 3채널로 확장하거나, crop을 GRAY로 바꾸거나, 논리적 인덱싱을 잘 써야함
        # 여기서는 색상 이미지에 마스크를 적용하므로, crop[np.logical_not(mask)] = [B,G,R] 형태가 맞음
        try:
            crop[np.logical_not(mask)] = [255, 0, 0] # 파란색으로 마스킹 (BGR 순서)
        except IndexError: # crop과 mask의 호환성 문제 등
            print("경고: 마스크 적용 중 오류 발생 in extract_face_part")
            return crop # 마스크 적용 실패 시 원본 crop 반환 또는 빈 배열

        return crop