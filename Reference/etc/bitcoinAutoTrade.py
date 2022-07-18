import time
import pyupbit
import datetime

access = "your-access"
secret = "your-secret"

def get_target_price(ticker, k):        #ticker : 어떤 코인인지 , k 
    """변동성 돌파 전략으로 매수 목표가 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

def get_start_time(ticker):
    """시작 시간 조회"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=1) #일봉으로 조회시 그날의 시작시간이 나온다. 
    start_time = df.index[0]    # 첫번째값이 시간값
    return start_time

def get_balance(ticker):
    """잔고 조회"""
    balances = upbit.get_balances()
    for b in balances:
        if b['currency'] == ticker:
            if b['balance'] is not None:
                return float(b['balance'])
            else:
                return 0
    return 0

def get_current_price(ticker):
    """현재가 조회"""
    return pyupbit.get_orderbook(tickers=ticker)[0]["orderbook_units"][0]["ask_price"]

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("autotrade start")

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()                       # 현재시간을 받아옴 
        start_time = get_start_time("KRW-BTC")              #9:00
        end_time = start_time + datetime.timedelta(days=1)  #9:00 + 1일

        # 매수 로직 -  9:00 < 현재 < #8:59:50
        if start_time < now < end_time - datetime.timedelta(seconds=10):
            target_price = get_target_price("KRW-BTC", 0.5)     #목표값 설정 
            current_price = get_current_price("KRW-BTC")        # 현재 값
            if target_price < current_price:        # 목표값 < 현재값
                krw = get_balance("KRW")            # 원화 조회
                if krw > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-BTC", krw*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
        # 매도 로직 - 8:59:51 ~ 9:00:00
        else:
            btc = get_balance("BTC")
            if btc > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-BTC", btc*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료
        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(1)