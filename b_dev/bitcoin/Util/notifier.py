import requests
from Util.const import *

def send_message(mes):
    if snsType == SNSType.Line:
        send_message_line(mes,LINE_API_TOKEN)
    elif snsType == SNSType.Telegram:
        send_message_telegram(mes, TELEGRAM_CHAT_ID, TELEGRAM_API_TOKEN)

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
