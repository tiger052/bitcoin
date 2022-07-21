####################
# Kakao API Module #
####################

import requests
import os.path
import json
import time

dic_apiData = {}                    # Api 관련 Data
dic_tokenData = {}                  # token 관련 Data
setting_path = "kakao_setting.json"  # 설정 파일 경로
token_path = "/kakao_token.json"  # 토큰 파일 경로

#------------------------#
# kakao Api Module 초기화
#------------------------#
def initKakao():
    global dic_apiData, dic_tokenData

    # 1.Api Setting 정보 파싱
    isSetupFile = os.path.isfile(setting_path)
    if isSetupFile:
        with open(setting_path, 'r') as file:
            dic_apiData = json.load(file)
            print(">> {}".format(dic_apiData))
    else:
        print("Cant load file. -> kakao_setting.json.")
        return

    # 2. Token 정보 파싱
    isTokenFile = os.path.isfile(token_path)
    if isTokenFile:
        dic_tokenData = getToken()
        print(">> {}".format(dic_tokenData))
    else:
        print("Cant load file 'kakao_token.json.' -> request Token()")
        requestToken()

#----------------------#
# Token File로 부터 파싱
#----------------------#
def getToken():
    with open(token_path, 'r') as file:
        token_data = json.load(file)
        return token_data

#-------------------#
# Token 정보 요청
#-------------------#
def requestToken():
    global dic_tokenData
    # 1.request Token Data 설정
    url = 'https://kauth.kakao.com/oauth/token'

    data = {
        'grant_type': 'authorization_code',
        'client_id': dic_apiData['rest_api_key'],
        'redirect_uri': dic_apiData['redirect_uri'],               # App 에서 등록한 redirect_url
        'code': dic_apiData['authorizeCode']                       # 사용자 코드(code)
    }

    # 2.request 처리
    response = requests.post(url, data=data)

    # 3.response 처리
    if response.status_code == 200:                                # 200 성공 시 처리
        token_data = response.json()
        print(">> request Token : {}".format(token_data))

        if 'access_token' in token_data:  # 성공 처리
            # 4.token 정보 저장
            dic_tokenData = token_data
            with open(r"" + token_path, "w") as fp:
                json.dump(dic_tokenData, fp)
        else:
            print("Bad Info - request Token")
    else:
        print("[ERROR] reqeust Token : " + str(response.status_code) + ", " + response.text)
        return

#-------------------#
# Token 정보 갱신
#-------------------#
def refreshToken():
    # 1.refresh Token Data 설정
    url = "https://kauth.kakao.com/oauth/token"

    data = {
        "grant_type": "refresh_token",                   # 얘는 단순 String임. "refresh_token"
        "client_id": f"{dic_apiData['rest_api_key']}",   # rest Api key
        "refresh_token": dic_tokenData['refresh_token']  # 여기가 위에서 얻은 refresh_token 값
    }
    # 2.request 처리
    response = requests.post(url, data=data)
    # 3.response 처리
    if response.status_code == 200:
        new_token = response.json()
        print(">> refrash Token : {}".format(new_token))
        dic_tokenData['access_token'] = new_token['access_token']
        with open(r"" + token_path, "w") as fp:
            json.dump(dic_tokenData, fp)
    else:
        print("[ERROR] refresh Token : " + str(response.status_code) + ", " + response.text)
        return

#-------------------#
# 친구 정보 조회
#-------------------#
def getFriendsList():
    # 1.request Friends List Data 설정
    header = {"Authorization": 'Bearer ' + dic_tokenData['access_token']}
    url = "https://kapi.kakao.com/v1/api/talk/friends"  # 친구 정보 요청

    # 2.request 처리
    response = requests.get(url, headers=header)

    # 3.response 처리
    if response.status_code == 200:

        result = json.loads(response.text)

        friends_list = result.get("elements")
        friends_id = []

        for friend in friends_list:
            friends_id.append(str(friend.get("uuid")))

        print(">> friends_list : {}".format(friends_list))
    else:
        print("[ERROR] getFriendsList : " + str(response.status_code) + ", " + response.text)
        return

#-----------#
# 메시지 전송
#-----------#
def sendToMeMessage(uuid, text):
    # 1.send To Message Data 설정
    header = {"Authorization": 'Bearer ' + dic_tokenData['access_token']}
    url = "https://kapi.kakao.com/v1/api/talk/friends/message/default/send"  # Api 주소
    data = {
        'receiver_uuids': '["{}"]'.format(uuid),
        "template_object": json.dumps({
            "object_type": "text",
            "text": ""+text,
            "link": {
                #"web_url": "https://www.google.co.kr/search?q=deep+learning&source=lnms&tbm=nws",
                #"mobile_web_url": "https://www.google.co.kr/search?q=deep+learning&source=lnms&tbm=nws"
            },
            "button_title": ""
        })
    }
    print(data)
    response = requests.post(url, headers=header, data=data)

    if response.status_code == 200:
        print(">> send To Message : {}".format(response.json()))
        pass
    else:
        print("[ERROR] sendToMeMessage : " + str(response.status_code) + ", " + response.text)
        if response.status_code == 401:
            refreshToken()
        return
