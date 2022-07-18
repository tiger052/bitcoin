from enum import Enum

class SNSType(Enum):
    Line = 0,
    Telegram = 1

#===== Config Info =====#
snsType = SNSType.Telegram

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