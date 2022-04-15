####################
# Upbit API Module #
####################

import os.path
import json
import pyupbit

upbit_path = "../live/upbit_setting.json"           # 토큰 파일 경로

#------------------------#
# PyUpbit 모듈 생성
#------------------------#
def create_instance():
    isUpbitFile = os.path.isfile(upbit_path)
    if isUpbitFile:
        with open(upbit_path, 'r') as file:
            dic_upbit = json.load(file)
        inst = pyupbit.Upbit(dic_upbit['upbit_access'], dic_upbit['upbit_secret'])
        return inst
    else:
        print("Cant load file 'upbit_setting.json.'")
        return None

#----------------------------------------------#
# 변동성 돌파 전략 목표가 조회 -  ticker : 코인 , k : 타겟 비율
#----------------------------------------------#
def get_target_price(ticker, k):                # ticker : 어떤 코인인지 , k
    """    df = pyupbit.get_ohlcv(ticker)              # 날짜 별로 내림 차순

    yesterday = df.iloc[-2]                     # 끝에서 두번째 행 (전일 데이터) -> iloc 행단위로 얻어옴
    today_open = yesterday['close']             # 당일 시가 (전일 종가 = 단일 시가)
    gap = yesterday['high'] - yesterday['low']  # 범위 = 전일 고가 - 전일 저가
    break_out_range = today_open + gap * k      # 매수 목표가 지정 = 시가 + (전일 고가 - 전일 저가) * 매수 비율

    return break_out_range"""
    df = pyupbit.get_ohlcv(ticker, interval="day", count=2)
    target_price = df.iloc[0]['close'] + (df.iloc[0]['high'] - df.iloc[0]['low']) * k
    return target_price

#----------------------------------------------#
# 티커 조회 : 티커
#----------------------------------------------#
def get_ticker(market='KRW'):
    tickers = pyupbit.get_tickers(market)
    return tickers

#----------------------------------------------#
# 시작 시간 조회 - ticker : 코인
#----------------------------------------------#
def get_start_time(ticker):

    df = pyupbit.get_ohlcv(ticker, interval="day", count=1)     # 일봉으로 조회시 그날의 시작시간이 나온다.
    start_time = df.index[0]    # 첫 번째값이 시간값
    return start_time

#----------------------------------------------#
# 현재가 조회 - ticker : 코인
#----------------------------------------------#
def get_current_price(ticker):
    orderbook = pyupbit.get_orderbook(ticker)
    return orderbook[0]["orderbook_units"][0]["ask_price"]      # get_orderbook 은 매도 매수가 리스트를 반환한다. linux
    #return orderbook["orderbook_units"][0]["ask_price"]  # get_orderbook 은 매도 매수가 리스트를 반환한다. window

#----------------------------------------------#
# 전일 5일 이동 평균 값 조회
#----------------------------------------------#
def get_yesterday_ma5(ticker):
    df = pyupbit.get_ohlcv(ticker)              # 일봉 테이블
    close = df['close']                         # 종가 컬럼
    ma = close.rolling(window=5).mean()         # 5 일 이동 평균을 계산하고 반환
    return ma[-2]                               # 전일 기준 5일 평균값

#----------------------------------------------#
# 보유 금액 조회
#----------------------------------------------#
def get_balance(upbit, ticker):
    balance = upbit.get_balance(ticker)         # 보유 금액 조회
    return balance

#----------------------------------------------#
# 매수 처리
#----------------------------------------------#
def buy_crypto_current(upbit, ticker):
    krw = upbit.get_balance(ticker)[2]              # 2번 인덱스 값이보유 중인 원화를 얻어 온다.
    orderbook = pyupbit.get_orderbook(ticker)       # 호가창 조회.
    sell_price = orderbook['asks'][0]['price']      # 최우선 매도 호가를 조회.
    unit = krw/float(sell_price)                    # 원화 잔고 / 최우선 매도가 나눠 구매 가능한 수량을 계산
    upbit.buy_market_order(ticker, unit * 0.9995)   # 매수 처리 (0.0005는 수수료 계산)

#----------------------------------------------#
# 매도 처리
#----------------------------------------------#
def sell_crypto_currency(upbit, ticker):
    unit = upbit.get_balance(ticker)[0]           # 본인 계좌 잔고 조회
    upbit.sell_market_order(ticker, unit)         # 전량 매도 처리



#instance = create_instance()
#result = get_start_time("KRW-BTC")
#result =  get_target_price("KRW-BTC", 0.8)
#print(result)
