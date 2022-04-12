import pyupbit
import datetime
import time
import kakaoControl
import upbitControl
from enum import Enum

class TradeState(Enum):
    ready = "ready"                     # 준비
    trading = "trading"                 # 트레이딩 중
    waiting = "waiting"                 # 대기 중

class TradeMode(Enum):
    break_out_range = 0                 # 변동성 돌파 전략
    break_out_range_and_ma5 = 1         # 변동성 돌파 전략 + 전일 기준 5일 이동 평균값
    reading = 2

class TradeCoin(Enum):                  # 트레이딩 할 코인 셋팅
    WAVE = "KRW-WAVES",
    AERGO = "KRW-AERGO",
    ELF = "KRW-ELF"
#['KRW-BTC', 'KRW-ETH', 'BTC-ETH', 'BTC-LTC', 'BTC-XRP', 'BTC-ETC', 'BTC-OMG', 'BTC-CVC', 'BTC-DGB', 'BTC-SC', 'BTC-SNT', 'BTC-WAVES', 'BTC-NMR', 'BTC-XEM', 'BTC-QTUM', 'BTC-BAT', 'BTC-LSK', 'BTC-STEEM', 'BTC-DOGE', 'BTC-BNT', 'BTC-XLM', 'BTC-ARDR', '


## Trading Setting #####
trademode = TradeMode.reading   # 트레이드 모드 설정
targetCoin = TradeCoin.WAVE     # 트레이드 할 Coin
tradeState = TradeState.ready   # 트레이드 상태
targetPercent = 0.8             # 변동성 돌파 목표치 비율
tradeVolumeMin = 5000           # 최소 거래 값 - 5000원 이상
feePercent = 0.9995             # 수수료 퍼센트
########################

def init():
    kakaoControl.initKakao()       # 카카오 Module 초기화
    kakaoControl.refreshToken()

def autoTradingTest():
    print(upbitControl.get_ticker())
    init()
    now = datetime.datetime.now()  # 현재시간을 받아옴
    #start_time = upbitControl.get_start_time("KRW-BTC")  # 9:00
    #end_time = start_time + datetime.timedelta(days=1)  # 9:00 + 1일
    start_time = now - datetime.timedelta(seconds=1)
    end_time = start_time + datetime.timedelta(seconds=10)  # 9:00 + 1일
    #
    print(now)
    print(start_time)
    print(end_time)
    global tradeState, targetCoin
    upbitControl.get_yesterday_ma5(targetCoin.value)
    print(targetCoin.value)
    while True:
        try:
            if tradeState == TradeState.ready:
                tradeState = TradeState.trading
                print(tradeState.value)
            now = datetime.datetime.now()
            if start_time < now < end_time:
                if tradeState == TradeState.waiting:
                    tradeState = TradeState.trading
                    print(tradeState.value)
                    time.sleep(1)
                    continue
                #print(targetCoin.value)
                target_price = upbitControl.get_target_price(targetCoin.value, targetPercent)  # 목표값 설정
                print("target : ", target_price, " coin : ", targetCoin.value)
                current_price = upbitControl.get_current_price(targetCoin.value)
                print(current_price)


                #if target_price < current_price:            # 목표값 < 현재값
                print(upbitControl.get_balance(upbitInst,ticker="KRW"))          # 보유 KRW
                print("all",upbitInst.get_amount('ALL'))                  # 총매수금액
                print(upbitControl.get_balance(upbitInst,ticker="KRW-BTC"))      # 비트코인 보유수량
                print(upbitControl.get_balance(upbitInst,ticker="KRW-XRP"))      # 리플 보유수량
                #print("원화 ", krw)
                    #if krw > 5000:  # 원화가 5000보다 크면
                print("111")
                btc = upbitControl.get_balance(upbitInst,targetCoin.value)
                print(btc)
            else:
                """if tradeState == TradeState.waiting:
                    tradeState = TradeState.trading
                    print(tradeState.value)
                    time.sleep(1)
                    continue"""
                print("waitng")

        except Exception as e:
            print(e)
        time.sleep(1)

def autoTradingLive():
    # 1. 초기화
    init()
    # 2. 트레이딩 시작 알림
    now = datetime.datetime.now()
    kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] Bitcoin 트래이딩 시작!!")

    # 3. 자동매매 시작
    if trademode == TradeMode.break_out_range:  # 변동성 돌파 전략 방법
        while True:
            try:
                # 3.1 시간 설정 (현재 , 당일 시작, 명일 시작)
                now = datetime.datetime.now()                               # 현재 시간을 받아옴
                start_time = upbitControl.get_start_time(targetCoin.value)  # 당일 시작 시간 - 9:00
                end_time = start_time + datetime.timedelta(days=1)          # 명일 시작 시간 - 9:00 (+ 1일)

                # 3.2 매수 로직 -  당일 9:00 < 현재 < # 명일 8:59:50
                if start_time < now < end_time - datetime.timedelta(seconds=10):
                    target_price = upbitControl.get_target_price(targetCoin.value, targetPercent)  # 목표값 설정
                    current_price = upbitControl.get_current_price(targetCoin.value)               # 현재 값

                    if target_price < current_price:  # 목표값 < 현재값
                        krw = upbitControl.get_balance("KRW")  # 원화 조회
                        if krw > tradeVolumeMin:  # 원화가 5000보다 크면
                            upbitInst.buy_market_order(targetCoin.value, krw * feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                        else:
                            print("have no money")

                # 3.3 매도 로직 - 명일 8:59:51 ~ 9:00:00
                else:
                    unit = upbitControl.get_balance(targetCoin.value)
                    upbitInst.sell_market_order(targetCoin.value, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
            except Exception as e:
                print(e)

            time.sleep(1)
    elif trademode == TradeMode.break_out_range_and_ma5:    # 변동성 돌파 전략 + 전일 기준 5일 이동 평균값
        while True:
            try:
                # 3.1 시간 설정 (현재 , 당일 시작, 명일 시작)
                now = datetime.datetime.now()                               # 현재 시간을 받아옴
                start_time = upbitControl.get_start_time(targetCoin.value)  # 당일 시작 시간 - 9:00
                end_time = start_time + datetime.timedelta(days=1)          # 명일 시작 시간 - 9:00 (+ 1일)

                # 3.2 매수 로직 -  당일 9:00 < 현재 < # 명일 8:59:50
                if start_time < now < end_time - datetime.timedelta(seconds=10):
                    target_price = upbitControl.get_target_price(targetCoin.value, targetPercent)  # 목표값 설정
                    current_price = upbitControl.get_current_price(targetCoin.value)               # 현재 값
                    ma5 = upbitControl.get_yesterday_ma5(targetCoin.value)

                    if (current_price > target_price) and (current_price > ma5):  # 목표가 뿐만 아니라 이동평균과 현재가를 비교한다
                        krw = upbitControl.get_balance("KRW")  # 원화 조회
                        if krw > tradeVolumeMin:  # 원화가 5000보다 크면
                            upbitInst.buy_market_order(targetCoin.value, krw * feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                        else:
                            print("have no money")

                # 3.3 매도 로직 - 명일 8:59:51 ~ 9:00:00
                else:
                    unit = upbitControl.get_balance(targetCoin.value)
                    upbitInst.sell_market_order(targetCoin.value, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
            except Exception as e:
                print(e)

            time.sleep(1)
    else:
        print("준비중")
        time.sleep(1)

upbitInst = upbitControl.create_instance()                            # Upbit instance
autoTradingTest()
#autoTradingLive()

