import cv2
import numpy as np
from personal_color_analysis import tone_analysis
from personal_color_analysis.detect_face import DetectFace # 사용자가 제공한 detect_face.py를 사용한다고 가정
from personal_color_analysis.color_extract import DominantColors
from colormath.color_objects import LabColor, sRGBColor, HSVColor
from colormath.color_conversions import convert_color

def analysis(imgpath):
    #######################################
    #           Face detection            #
    #######################################
    df = DetectFace(imgpath)
    if not df.face_detected: # DetectFace에서 얼굴 감지/랜드마크 추출에 실패했는지 확인
        print(f"오류: {imgpath} 이미지에서 얼굴 특징을 추출할 수 없어 퍼스널 컬러 분석을 진행할 수 없습니다.")
        return # 분석 중단

    face = [df.left_cheek, df.right_cheek,
            df.left_eyebrow, df.right_eyebrow,
            df.left_eye, df.right_eye]

    #######################################
    #         Get Dominant Colors         #
    #######################################
    temp = []
    clusters = 4
    valid_face_parts_count = 0 # 유효한 얼굴 부위 개수 카운트

    for f_part_image in face: # 변수명을 f에서 f_part_image로 변경하여 명확성 향상
        # 얼굴 부위 이미지가 유효한 OpenCV 이미지(NumPy 배열)인지 확인
        if f_part_image is not None and isinstance(f_part_image, np.ndarray) and f_part_image.size > 0:
            try:
                dc = DominantColors(f_part_image, clusters)
                face_part_color, _ = dc.getHistogram()
                if len(face_part_color) > 0: # getHistogram에서 유효한 색상이 추출되었는지 확인
                    temp.append(np.array(face_part_color[0]))
                    valid_face_parts_count += 1
                else:
                    # 유효한 색상을 못 찾았을 경우
                    temp.append(np.array([0, 0, 0])) # 대표 색상으로 검은색을 임시 사용
                    print(f"경고: {imgpath} 이미지의 특정 얼굴 부위에서 대표 색상을 추출하지 못했습니다.")
            except Exception as e: # DominantColors 또는 getHistogram에서 예외 발생 시
                temp.append(np.array([0,0,0]))
                print(f"경고: {imgpath} 이미지의 얼굴 부위 색상 추출 중 오류 발생: {e}")
        else:
            # 얼굴 부위 이미지가 유효하지 않을 경우 처리
            temp.append(np.array([0, 0, 0])) # 대표 색상으로 검은색을 임시 사용
            print(f"경고: {imgpath} 이미지에서 유효하지 않은 얼굴 부위 데이터를 받았습니다 (비어 있거나 None).")

    # 모든 주요 얼굴 부위(뺨, 눈썹, 눈 각각 2개씩, 총 6개)에서 색상 추출에 성공했는지 확인
    # 여기서는 최소한 3가지 주요 부위(뺨 평균, 눈썹 평균, 눈 평균)를 위한 데이터가 필요하다고 가정
    # temp 리스트의 길이가 6이고, valid_face_parts_count가 특정 임계값 이상이어야 함
    # 예를 들어, 뺨(2), 눈썹(2), 눈(2) 중 각각 하나 이상은 성공해야 한다고 가정할 수 있음
    # 좀 더 간단하게는, 전체 유효 부위가 특정 개수 미만이면 실패 처리
    MIN_VALID_PARTS_REQUIRED = 3 # 예시: 최소 3개 부위에서 유효한 색상 필요 (뺨, 눈썹, 눈 각각 대표값)
                                 # 이 값은 상황에 맞게 조절 필요
    
    # temp 리스트 길이는 항상 6이 되도록 위에서 처리했으므로,
    # valid_face_parts_count로 실제 유효했던 부위 수를 판단
    if valid_face_parts_count < MIN_VALID_PARTS_REQUIRED : # 유효한 부위가 너무 적으면 분석 불가
        print(f"오류: {imgpath} 이미지에서 분석에 필요한 충분한 얼굴 부위의 색상을 추출하지 못했습니다. (유효 부위 수: {valid_face_parts_count}/6)")
        return # 분석 중단

    # 각 부위별 평균 색상 계산
    # temp 리스트의 인덱스는 face 리스트 순서와 동일: [왼쪽뺨, 오른쪽뺨, 왼쪽눈썹, 오른쪽눈썹, 왼쪽눈, 오른쪽눈]
    # temp[0], temp[1]이 뺨 색상이므로, 이들이 유효했는지 (0,0,0이 아닌지) 확인하는 로직 추가 가능
    cheek = np.mean([temp[0], temp[1]], axis=0)
    eyebrow = np.mean([temp[2], temp[3]], axis=0)
    eye = np.mean([temp[4], temp[5]], axis=0)

    # 만약 cheek, eyebrow, eye 중 하나라도 [0,0,0] (실패 시 임시값)이라면,
    # 이는 해당 부위의 양쪽 모두에서 색상 추출에 실패했음을 의미할 수 있음.
    # 이 경우, 더 정교한 오류 처리나 기본값 사용 로직이 필요할 수 있음.
    # 예를 들어, np.all(cheek == 0) 등으로 확인.

    Lab_b, hsv_s = [], []
    color_parts = [cheek, eyebrow, eye] # 변수명 명확히
    
    try:
        for i in range(3):
            # 각 color_part (cheek, eyebrow, eye 평균값)가 유효한 RGB 값인지 확인
            # 예를 들어, 모든 요소가 0인 경우 (색상 추출 완전 실패) sRGBColor 변환 시 문제 발생 가능성 있음
            # 하지만 is_upscaled=True 이므로 0~255 범위로 처리될 것임.
            # 다만, [0,0,0] 색상에 대한 분석 결과가 의미 없을 수 있음.
            if np.all(color_parts[i] == 0) and i < 2 : # 눈 색깔은 어두울 수 있으므로 뺨과 눈썹만 체크 (예시)
                print(f"경고: {imgpath} 이미지의 주요 부위(뺨/눈썹) 평균 색상이 [0,0,0]입니다. 분석 결과가 정확하지 않을 수 있습니다.")

            rgb = sRGBColor(color_parts[i][0], color_parts[i][1], color_parts[i][2], is_upscaled=True)
            lab = convert_color(rgb, LabColor, through_rgb_type=sRGBColor)
            hsv = convert_color(rgb, HSVColor, through_rgb_type=sRGBColor)
            Lab_b.append(float(format(lab.lab_b,".2f")))
            hsv_s.append(float(format(hsv.hsv_s,".2f"))*100)
    except Exception as e:
        print(f"오류: {imgpath} 이미지의 색상 변환 중 오류 발생: {e}")
        return

    # print(f'{imgpath} - Lab_b[skin, eyebrow, eye]: {Lab_b}')
    # print(f'{imgpath} - hsv_s[skin, eyebrow, eye]: {hsv_s}')
    #######################################
    #      Personal color Analysis        #
    #######################################
    Lab_weight = [30, 20, 5]
    hsv_weight = [10, 1, 1]
    
    # is_warm, is_spr, is_smr 함수들이 Lab_b, hsv_s 리스트의 값에 의존하므로,
    # 이 값들이 정상적으로 채워졌는지 (예: 3개의 요소를 모두 갖는지) 확인하는 것이 좋으나,
    # 위에서 색상 변환 실패 시 return 하므로, 이 부분에 도달했다면 3개의 요소는 있을 것임.

    if(tone_analysis.is_warm(Lab_b, Lab_weight)):
        if(tone_analysis.is_spr(hsv_s, hsv_weight)):
            tone = '봄웜톤(spring)'
        else:
            tone = '가을웜톤(fall)'
    else:
        if(tone_analysis.is_smr(hsv_s, hsv_weight)):
            tone = '여름쿨톤(summer)'
        else:
            tone = '겨울쿨톤(winter)'
    # Print Result
    print('{}의 퍼스널 컬러는 {}입니다.'.format(imgpath, tone))

    # 핵심 변경: tone 값을 반환하도록 추가!
    return tone # <--- 이 줄을 추가합니다.