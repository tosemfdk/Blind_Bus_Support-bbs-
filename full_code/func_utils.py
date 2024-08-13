import psycopg2
import requests
import xml.etree.ElementTree as ET
import cv2
from collections import Counter
import cv2
from ultralytics import YOLO
import pyaudio
from google.cloud import speech
from google.cloud import texttospeech

# YOLO 모델을 초기화하고 비디오에서 프레임을 읽는 기능을 제공
# 비디오 파일에서 프레임을 일정한 간격으로 추출하여 처리할 수 있게 함
class YOLOVideoCapture:
    def __init__(self, model_path, video_path):
        # YOLO 모델 초기화
        self.model = YOLO(model_path)
        self.model.overrides['verbose'] = False

        # 비디오 캡처 초기화
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_interval = int(self.fps / 5)
    
    def read_frames(self):
        frames = []
        while self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break

            if int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) % self.frame_interval == 0:
                frames.append(frame)
                if len(frames) == 15:
                    yield frames
                    frames = []
        
        if frames:
            yield frames
    
    def release(self):
        self.cap.release()

class ImageProcessor:
    @staticmethod
    def preprocess_image(image):
        """이미지 전처리 함수."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6, 6))
        gray = clahe.apply(gray)
        blurred = cv2.GaussianBlur(cv2.medianBlur(gray, 7), (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, morph_kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, morph_kernel)
        
        num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
        for i in range(1, num_labels):
            if stats[i, cv2.CC_STAT_AREA] < 70:
                binary[labels == i] = 0
        
        return binary



class API():
    def __init__(self):
        pass
            
    def database_query(self, table, key1, key2, val):
        """
        지정된 테이블에서 키와 값을 기준으로 데이터를 조회합니다.

        Parameters:
            table (str): 조회할 table의 이름. EX) bus, station.
            key1 (str): 해당 테이블에 리턴받고자하는 column의 key값.
            key2 (str): 해당 테이블 에서 검색할 value가 해당하는 column.
            val (str): 조회 기준이 될 값.

        Returns:
            list: 조회 결과를 리스트 형태로 반환.

        Raises:
            DatabaseError: 데이터베이스 조회 중 오류가 발생한 경우.
        """
        #데이터베이스에 연결시도
        try:
            # 데이터베이스 연결 & 커넥트 객체 생성
            conn = psycopg2.connect(host="122.44.85.37", dbname="postgres", user="postgres", password="postgres")
        except:
            print("Not Connected!.")

        # 쿼리를 수행하는 cursor객체 생성
        cursor = conn.cursor()

        # 쿼리문
        sql_query = f"SELECT {key1} FROM {table} WHERE {key2} = %s;"

        # 쿼리실행
        cursor.execute(sql_query, (val,))
        #fetchone은 쿼리에 해당하는 열을 튜플형태로 반환, 없다면 None
        query_result = cursor.fetchone()

        # 예외 처리
        if query_result:
            print("queryed value : ", query_result[0])
        else:
            print("No value found with the given value")


        # 데이터베이스 연결 끊기
        conn.close()
        return query_result
    
    # 특정 정류장의 정보(그 정류장에서 운행하는 버스들, 도착정보)
    def station_bus_list(self, station_result):
        url = 'http://ws.bus.go.kr/api/rest/arrive/getLowArrInfoByStId'
        service_key = "lnGvRUsSrOgezp/xjHmRf1XJipLQd9ANFdkUk5w2kB1FaTDTAcS88zmKBViC6HYFRcWfhGjkuNQD85aNrvoTTw=="

        params ={'serviceKey' : service_key,
                'stId' : str(station_result) }

        response = requests.get(url, params=params)
        return response.content

    # def station_bus_list(self, station_result):
    #     url = 'http://ws.bus.go.kr/api/rest/arrive/getLowArrInfoByStId'
    #     service_key = "your_valid_service_key"

    #     params = {
    #         'serviceKey': service_key,
    #         'stId': str(station_result)
    #     }

    #     print(f"Calling API with parameters: {params}")  # 파라미터 로깅
    #     response = requests.get(url, params=params)
    #     if response.status_code == 200:
    #         print("API 호출 성공, 응답 데이터: ", response.text)
    #         return response.content
    #     else:
    #         print(f"API 호출 실패, 상태 코드: {response.status_code}, 응답: {response.text}")
    #         return None

    #  특정 버스 노선이 경유하는 버스 정류소의 정보
    def bus_station_list(self, bus_result):
        url = 'http://ws.bus.go.kr/api/rest/busRouteInfo/getStaionByRoute'
        service_key = 'lnGvRUsSrOgezp/xjHmRf1XJipLQd9ANFdkUk5w2kB1FaTDTAcS88zmKBViC6HYFRcWfhGjkuNQD85aNrvoTTw=='

        params ={'serviceKey' : service_key,
                'busRouteId' : str(bus_result) }

        response = requests.get(url, params=params)
        return response.content


    # 정류소 노선별 교통약자 도착예정정보
    def station_arrival_info(self, station_result, bus_result, ord):
        url = 'http://ws.bus.go.kr/api/rest/arrive/getLowArrInfoByRoute'
        service_key = 'lnGvRUsSrOgezp/xjHmRf1XJipLQd9ANFdkUk5w2kB1FaTDTAcS88zmKBViC6HYFRcWfhGjkuNQD85aNrvoTTw=='



        params ={'serviceKey' : service_key,
                'stId' : str(station_result),
                'busRouteId' : str(bus_result),
                'ord' : str(ord) }

        response = requests.get(url, params=params)
        return response.content
    
        #  좌표기반 버스정류장 위치 조회
    def station_pose(self, X_location, Y_location, radius):
        url = 'http://ws.bus.go.kr/api/rest/busRouteInfo/getStaionByRoute'
        service_key = 'lnGvRUsSrOgezp/xjHmRf1XJipLQd9ANFdkUk5w2kB1FaTDTAcS88zmKBViC6HYFRcWfhGjkuNQD85aNrvoTTw=='

        params ={'serviceKey' : service_key,
                'tmX' : str(X_location),
                'tmY' : str(Y_location),
                'radius' : str(radius)
                }

        response = requests.get(url, params=params)
        return response.content

    # xml 값에서 특정 val라는 tag안에 있는 item을 가져오는 함수
    def find_xml_val(self, root, val):
        item_list = []
        for item in root.findall(".//itemList"):
            item1 = item.find(str(val)).text  # val에 해당하는 태그의 텍스트 내용을 가져옵니다.
            item_list.append(item1)
        return item_list

    # 리스트에서 일치하는 값을 찾아서 True값과 인덱스를 반환해준다.
    def find_api_val(self, list, value_to_find):
        for i, val in enumerate(list):
            if str(val)==str(value_to_find):
                print(f"value {value_to_find} found at index {i}")
                return i, True
        print("could not found the value in the list")
        return None, False
    


# class ImageProcessor:
#     @staticmethod
#     def preprocess_image(image):
#         """이미지 전처리 함수."""
#         gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
#         clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(6, 6))
#         gray = clahe.apply(gray)
#         blurred = cv2.GaussianBlur(cv2.medianBlur(gray, 7), (5, 5), 0)
#         _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
#         morph_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
#         binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, morph_kernel)
#         binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, morph_kernel)
        
#         num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
#         for i in range(1, num_labels):
#             if stats[i, cv2.CC_STAT_AREA] < 70:
#                 binary[labels == i] = 0
        
#         return binary



# 프레임을 처리하여 번호판을 인식하고, 인식된 번호를 데이터베이스에서 조회하는 기능을 제공
# YOLO 모델을 사용하여 번호판을 감지하고, EasyOCR을 사용하여 번호판의 텍스트를 인식
class FrameProcessor:
    def __init__(self, model, plate_class_indices, reader, width, height, padding, min_confidence):
        self.model = model
        self.plate_class_indices = plate_class_indices
        self.reader = reader
        self.width = width
        self.height = height
        self.padding = padding
        self.min_confidence = min_confidence
        self.processed_numbers = set()
    
    def process_frame(self, frames):
        ocr_results = []

        for frame in frames:
            results = self.model(frame)
            boxes = results[0].boxes if len(results) > 0 else []

            for box in boxes:
                cls = int(box.cls)
                if cls in self.plate_class_indices:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    x1, y1 = max(x1 - self.padding, 0), max(y1 - self.padding, 0)
                    x2, y2 = min(x2 + self.padding, self.width), min(y2 + self.padding, self.height)

                    plate_image = frame[y1:y2, x1:x2]
                    if plate_image.size == 0:
                        continue

                    preprocessed_img = ImageProcessor.preprocess_image(plate_image)
                    ocr_result = self.reader.readtext(preprocessed_img, detail=1)

                    for res in ocr_result:
                        text, confidence = res[1], res[2]
                        if confidence >= self.min_confidence:
                            text = ''.join(filter(str.isdigit, text))
                            if 2 <= len(text) <= 4:
                                ocr_results.append(text)

        if ocr_results:
            most_common_text = Counter(ocr_results).most_common(1)[0][0]
            if most_common_text not in self.processed_numbers:
                print(f"Detected text: {most_common_text}")
                return most_common_text

        return None


#=========================== TTS =============================
def text_to_speech_ssml(ssml_text, output_file):
    client = texttospeech.TextToSpeechClient()

    # SSML 입력 설정
    synthesis_input = texttospeech.SynthesisInput(ssml=ssml_text)

    # 음성 설정
    voice = texttospeech.VoiceSelectionParams(
        language_code="ko-KR",
        ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
    )

    # 오디오 설정
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )

    # 음성 합성 요청
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )

    # 음성 파일 저장
    with open(output_file, "wb") as out:
        out.write(response.audio_content)
        print(f'Audio content written to file "{output_file}"')
