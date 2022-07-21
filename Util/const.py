from enum import Enum

class SNSType(Enum):
    Line = 0,
    Telegram = 1

class ProcessState(Enum):
    processing = "processing"                   # 처리중
    complete = "waiting"                        # 완료

class TradeMode(Enum):
    break_out_range = "변동성 돌파 전략"                                    # 변동성 돌파 전략
    break_out_range_and_ma5 = "변동성 돌파 + 5일 이동 평균 전략"              # 변동성 돌파 전략 + 전일 기준 5일 이동 평균값
    break_out_range_and_down_sell = "변동성 돌파 전략 + 하락시 매도 전략"      # 매수 : 변동성 돌파 전략 , 매도 : 일정 기준 하락시
    break_out_range_and_asking_buy_down_sell = "변동성 돌파 전략 + 호가 비교 + 하락시 매도 전략"  # 매수 : 변동성 돌파 전략 , 매도 : 일정 기준 하락시
    reading = "준비중"

#===== Config Info =====#
snsType = SNSType.Telegram
logFileName = "../Log/output.log"

#=====SNS Info=====#
#1.Line Token - J1 Stock
LINE_API_TOKEN = "6WCqsYSHGmv6YO7DTd2bk16uXaVdXCvEUdNsEddqMyf"
LINE_URL = 'https://notify-api.line.me/api/notify'

#2.Telegram - J1 bot
TELEGRAM_API_TOKEN = "5429809700:AAGuHFBSl9FIHMwdyhjrQAVdpRWHimCy20g"
TELEGRAM_CHAT_ID = "5457683354"
#TELEGRAM_URL = str.format("https://api.telegram.org/bot{}/sendmessage?chat_id={}&text=",TELEGRAM_API_TOKEN, TELEGRAM_CHAT_ID)
TELEGRAM_URL = "https://api.telegram.org/bot{}/sendmessage?chat_id={}&text={}"

#3.Kakao