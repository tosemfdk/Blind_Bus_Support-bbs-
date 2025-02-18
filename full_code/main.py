from func_utils import API, YOLOVideoCapture, FrameProcessor, text_to_speech_ssml, gps_sub, recognize_speech_from_audio, extract_bus_number, determine_intent, record_audio
import psycopg2
import requests
import xml.etree.ElementTree as ET
import threading
from queue import Queue
import easyocr
import os
import pygame
import rospy
from sensor_msgs.msg import NavSatFix
import sys
import simpleaudio as sa
from pydub import AudioSegment
import numpy as np
import time

start_time = time.time()


# 환경 변수 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = '/home/minseokim521/catkin_ws/src/bus/zippy-brand-429513-k7-6ef67897540d.json'

# 비디오 경로와 모델 경로 설정
# video_path = '/home/LOE/workspace/yolo/Archive/vid/KakaoTalk_20240812_133651375.mp4'
model_path = "/home/minseokim521/catkin_ws/src/bus/Blind_Bus_Support-bbs-/models/best_3000_n.pt"
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------
                                                    YOLO + OCR section
------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
yolo_ocr_start = time.time()


# YOLO 비디오 캡처와 EasyOCR 초기화
video_capture = YOLOVideoCapture(model_path)
easy_ocr = easyocr.Reader(['en'], gpu=True)

# 번호판 인식 클래스 이름 설정 및 인덱스 확인
plate_class_names = ['front_num', 'side_num', 'back_num']
plate_class_indices = [idx for idx, name in video_capture.model.names.items() if name in plate_class_names]

# YOLO 모델로 프레임 처리
padding = 5
min_confidence = 0.8
frame_processor = FrameProcessor(
    video_capture.model, plate_class_indices, easy_ocr,
    video_capture.width, video_capture.height, padding, min_confidence
)
ocr_number = []
# 비디오에서 프레임을 읽어와 처리
for i, frames in enumerate(video_capture.read_frames()):
    for frame in frames:
        results = video_capture.model(frame)
        

    ocr_number.append(frame_processor.process_frame(frames))
    if ocr_number[i]:
        print(f"OCR 결과로 추출된 번호판: {ocr_number[i]}")
        
print(f"ocr_number : {ocr_number}")


# ocr결과에서 None을 제거
filtered_ocr_numbers = [num for num in ocr_number if num is not None]


print(f"filtered_ocr_number : {filtered_ocr_numbers}")


# 비디오 캡처 해제
video_capture.release()


if ocr_number[0] == None:
    msg1 = "아무 번호도 인식되지 않았습니다."
    print("아무 번호도 인식되지 않았습니다.")
    text_to_speech_ssml(msg1, "ocr.mp3")
        
    # 소리재생

    print('sound playing')

    # MP3 파일 로드
    sound = AudioSegment.from_mp3("ocr.mp3")

    # WAV 파일로 변환
    sound.export("ocr.wav", format="wav")

    # 오디오 파일 로드
    wave_obj = sa.WaveObject.from_wave_file("ocr.wav")

    # 오디오 재생
    play_obj = wave_obj.play()
    play_obj.wait_done()  # 재생이 끝날 때까지 기다림

    print('sound_ends')
    print("end of the code")
    exit()
        



#걸린 시간 출력
yolo_ocr_end = time.time()

print(f"Yolo + OCR section took {yolo_ocr_end - yolo_ocr_start} seconds. ")

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------
                                                        API section
------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
api_start = time.time()


# GPS 데이터를 받아오고 그 값을 변수에 저장

latitude, longitude = gps_sub()
# latitude, longitude = 126.90509208, 37.5158657465

# if latitude is None or longitude is None:
#     print("Failed to get GPS coordinates")
# else:
#     print(f"Received coordinates: Latitude={latitude}, Longitude={longitude}")
bus_api = API()

Bus_num = filtered_ocr_numbers[0]

#데이터 베이스 상에서 버스 번호와 정류소 이름에 해당하는 id값 가져오기
bus_result = bus_api.database_query('bus', 'routeid', 'bus_id', Bus_num)
station_list = bus_api.database_query_specific_column("station", 'node_id')
station_name_list = bus_api.database_query_specific_column("station", 'station_name')
X_locations = bus_api.database_query_specific_column("station", 'X_location')
Y_locations = bus_api.database_query_specific_column("station", 'Y_location')

# 리스트 평탄화
X_locations = [x[0] for x in X_locations]
Y_locations = [y[0] for y in Y_locations]

# 가장 가까운 정류소 인덱스 찾기
index = bus_api.find_nearest_index(longitude, latitude, X_locations, Y_locations)
station_name = station_name_list[index]
station_id = station_list[index]

print(f"찾아낸 정류소의 이름 :{station_name}, 찾아낸 정류소의 id :{station_id}")

if bus_result == None:
    print("OCR상의 버스 번호가 DB와 일치하지 않습니다.")
    exit()
# api 상에서 station id에 해당하는 정류소에 운행하는 버스정보 가져오기
response2 = bus_api.station_bus_list(station_id[0])

#xml 값을 가져옴
root2 = ET.fromstring(response2)

# 정류소에서 운행하는 버스 이름 정보 리스트
bus_list = bus_api.find_xml_val(root2, "busRouteAbrv")

# 버스 리스트에서 인식한 버스 정보가 있는지 찾음
index, result = bus_api.find_api_val(bus_list, Bus_num)

isArrive1 = []
arrmsg1_list = []
arrmsg2_list = []

if result:
    isArrive1 = bus_api.find_xml_val(root2, "isArrive1")
    arrmsg1_list = bus_api.find_xml_val(root2, "arrmsg1")
    arrmsg2_list = bus_api.find_xml_val(root2, "arrmsg2")
else:
    exit()
msg1, msg2, msg3 = 0,0,0

# 변수 출력
if not(isArrive1[index]):
    msg1 = f"{Bus_num}번 버스가 도착했습니다."
    print(msg1)
    
else:
    msg1 = f"{Bus_num}번 버스가 도착하지 않았습니다."
    print(msg1)
    
msg2 = "첫번째 버스 도착 예정시간 :" + arrmsg1_list[index] 
msg3 = "두번째 버스 도착 예정시간 :" + arrmsg2_list[index] 
print(msg2)
print(msg3)

api_end = time.time()
print(f"API section took {api_end - api_start} seconds.")

'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------
                                                        TTS section
------------------------------------------------------------------------------------------------------------------------------------
------------------------------------------------------------------------------------------------------------------------------------
'''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
tts_start = time.time()

# 텍스트를 mp3파일로 저장, 이미 있는경우 덮어씀
text_to_speech_ssml(msg1 + msg2 + msg3, "ocr.mp3")

# 소리재생
print('sound playing')

# MP3 파일 로드
sound = AudioSegment.from_mp3("ocr.mp3")

# WAV 파일로 변환
sound.export("ocr.wav", format="wav")

# 오디오 파일 로드
wave_obj = sa.WaveObject.from_wave_file("ocr.wav")

# 오디오 재생
play_obj = wave_obj.play()
play_obj.wait_done()  # 재생이 끝날 때까지 기다림

print('sound_ends')
print("end of the code")

tts_end = time.time()
print(f"TTS section took {tts_end - tts_start} seconds.")
end_time = time.time()

print(f"Total excution time took {end_time - start_time} seconds.")


