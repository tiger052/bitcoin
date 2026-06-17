from enum import Enum

class TradeType(Enum):
    Live = 0,           # 실제 거래
    Test = 1            # 모의 거래

class SNSType(Enum):
    Line = 0,
    Telegram = 1

class BuyStrategyType(Enum):
    MA5_CROSSOVER = "MA5_CROSSOVER"
    OPEN_BREAKOUT = "OPEN_BREAKOUT"
    CANDLE_3_GREEN = "CANDLE_3_GREEN"

class SellStrategyType(Enum):
    HODL_NO_LOSS = "HODL_NO_LOSS"
    TRAILING_STOP_NO_LOSS = "TRAILING_STOP_NO_LOSS"
    FIXED_STOP_LOSS = "FIXED_STOP_LOSS"

class ProcessState(Enum):
    processing = "processing"                   # 처리중
    complete = "waiting"                        # 완료

class TradeMode(Enum):
    break_out_range = "변동성 돌파 전략"                                    # 변동성 돌파 전략
    break_out_range_and_ma5 = "변동성 돌파 + 5일 이동 평균 전략"              # 변동성 돌파 전략 + 전일 기준 5일 이동 평균값
    break_out_range_and_down_sell = "변동성 돌파 전략 + 하락시 매도 전략"      # 매수 : 변동성 돌파 전략 , 매도 : 일정 기준 하락시
    break_out_range_and_asking_buy_down_sell = "변동성 돌파 전략 + 호가 비교 + 하락시 매도 전략"  # 매수 : 변동성 돌파 전략 , 매도 : 일정 기준 하락시
    reading = "준비중"

class BreakOutRangeUniverse(Enum):
    limit_price = "제한된 금액 선별"
    drawdown_rank = "낙폭 순위 선별"
    reading = "준비중"

import os
import json

#===== Config Info =====#
tradeType = TradeType.Live
snsType = SNSType.Telegram

#=====Upbit Info=====#
UPBIT_OPEN_API_SERVER_URL = "https://api.upbit.com"

# Global credentials loaded dynamically
UPBIT_ACCESS_KEY = ""
UPBIT_SECRET_KEY = ""
LINE_API_TOKEN = ""
TELEGRAM_API_TOKEN = ""
TELEGRAM_CHAT_ID = ""

def load_secrets():
    global UPBIT_ACCESS_KEY, UPBIT_SECRET_KEY, LINE_API_TOKEN, TELEGRAM_API_TOKEN, TELEGRAM_CHAT_ID
    secrets_path = "secrets.json"
    
    # Default placeholder config
    default_secrets = {
        "upbit_access_key": "YOUR_UPBIT_ACCESS_KEY",
        "upbit_secret_key": "YOUR_UPBIT_SECRET_KEY",
        "telegram_api_token": "YOUR_TELEGRAM_API_TOKEN",
        "telegram_chat_id": "YOUR_TELEGRAM_CHAT_ID",
        "line_api_token": "YOUR_LINE_API_TOKEN"
    }
    
    try:
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            UPBIT_ACCESS_KEY = data.get("upbit_access_key", "")
            UPBIT_SECRET_KEY = data.get("upbit_secret_key", "")
            TELEGRAM_API_TOKEN = data.get("telegram_api_token", "")
            TELEGRAM_CHAT_ID = data.get("telegram_chat_id", "")
            LINE_API_TOKEN = data.get("line_api_token", "")
        else:
            with open(secrets_path, "w", encoding="utf-8") as f:
                json.dump(default_secrets, f, indent=2)
            print(">> [Warning] secrets.json not found. Created a default template. Please fill it in.")
    except Exception as e:
        print(f">> [Error Loading Secrets] {e}")

# Load credentials immediately
load_secrets()

#=====SNS Info=====#
LINE_URL = 'https://notify-api.line.me/api/notify'
TELEGRAM_URL = "https://api.telegram.org/bot{}/sendmessage?chat_id={}&text={}"

#3.Kakao