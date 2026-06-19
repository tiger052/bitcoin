import requests
from Util.const import *

def send_message(mes):
    try:
        # 토큰 설정이 비어있거나 플레이스홀더 기본값이면 알림 생략
        if snsType == SNSType.Telegram:
            if not TELEGRAM_API_TOKEN or "YOUR_" in TELEGRAM_API_TOKEN or not TELEGRAM_CHAT_ID or "YOUR_" in TELEGRAM_CHAT_ID:
                return
            send_message_telegram(mes, TELEGRAM_CHAT_ID, TELEGRAM_API_TOKEN)
        elif snsType == SNSType.Line:
            if not LINE_API_TOKEN or "YOUR_" in LINE_API_TOKEN:
                return
            send_message_line(mes, LINE_API_TOKEN)
    except Exception as e:
        # 알림 전송 에러가 발생해도 봇의 핵심 트레이딩 루프가 멈추지 않도록 예외 차단 및 로깅만 수행
        print(f">> [Notification Error] {e}")

""" 
[Line Bot에 메세지 보내기]
message : 메시지, token : API 토큰
"""
def send_message_line(message, token=None):

    try:
        response = requests.post(
            LINE_URL,
            headers={
                'Authorization': 'Bearer ' + token
            },
            data={
                'message': message
            }
        )
        status = response.json()['status']
        # 전송 실패 체크
        if status != 200:
            # 에러 발생 시에만 로깅
            raise Exception('Fail need to check. Status is %s' % status)

    except Exception as e:
        raise Exception(e)

""" 
[Telegram Bot에 메세지 보내기]
message : 메시지, chatId : 채팅 ID, token : API 토큰
"""
def send_message_telegram(message, chatId, token):
    try:
        url = str.format(TELEGRAM_URL,token,chatId,message)
        response = requests.get(url)

        # 전송 실패 체크
        if response.status_code != 200:
            # 에러 발생 시에만 로깅
            raise Exception('Fail need to check. Status is %s' % response.status_code)

    except Exception as e:
        raise Exception(e)

if __name__ == "__main__":
    #snsType = snsType.Line
    #send_message("test")
    #print(list(SNSType))
    pass
