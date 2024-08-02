from func_utils import bus_station_list, station_arrival_info, find_xml_val, database_query, station_bus_list, find_api_val
import psycopg2
import requests
import xml.etree.ElementTree as ET
print("hi")

Bus_num = "5618"
Station_name = "영등포역"

#데이터 베이스 상에서 버스 번호와 정류소 이름에 해당하는 id값 가져오기
bus_result, station_result = database_query(Bus_num, Station_name)

# api 상에서 station id에 해당하는 정류소에 운행하는 버스정보 가져오기
response1 = station_bus_list(station_result[0])

#xml 값을 가져옴
root1 = ET.fromstring(response1)

# 정류소에서 운행하는 버스 이름 정보 리스트
bus_list = find_xml_val(root1, "busRouteAbrv")

# 버스 리스트에서 인식한 버스 정보가 있는지 찾음
index, result = find_api_val(bus_list, Bus_num)

isArrive1 = []
arrmsg1_list = []
arrmsg2_list = []
if result:
    isArrive1 = find_xml_val(root1, "isArrive1")
    arrmsg1_list = find_xml_val(root1, "arrmsg1")
    arrmsg2_list = find_xml_val(root1, "arrmsg2")


# 변수 출력
if not(isArrive1[index]):
    print("첫번째 버스가 도착했습니다.")
else:
    print("첫번째 버스가 도착하지 않았습니다.")
print("첫번째 버스 도착 예정시간 :", arrmsg1_list[index])
print("두번째 버스 도착 예정시간 :", arrmsg2_list[index])

print("end of the code")
