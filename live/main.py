import pyupbit
import datetime
import time
import kakaoControl
import upbitControl
from enum import Enum
import os.path

class TradeState(Enum):
    ready = "ready"                             # 준비
    trading = "trading"                         # 트레이딩 중
    waiting = "waiting"                         # 대기 중

class TradeMode(Enum):
    break_out_range = "변동성 돌파 전략"                                    # 변동성 돌파 전략
    break_out_range_and_ma5 = "변동성 돌파 + 5일 이동 평균 전략"              # 변동성 돌파 전략 + 전일 기준 5일 이동 평균값
    break_out_range_and_down_sell = "변동성 돌파 전략 + 하락시 매도 전략"      # 매수 : 변동성 돌파 전략 , 매도 : 일정 기준 하락시
    reading = "준비중"

tickerlist = []                                 # Tickers
buy_price = 0                                   # 매수 시 금액
sell_price = 0                                  # 판매 하기 위한 금액
max_price = 0                                   # 매수 후 최고 가격

## Trading Setting #####
trademode = TradeMode.break_out_range           # 트레이드 모드 설정
targetCoin = "KRW-XRP"                          # 트레이드 할 Coin
tradeState = TradeState.ready                   # 트레이드 상태
targetPercent = 0.5                             # 변동성 돌파 목표치 비율
tradeVolumeMin = 5000                           # 최소 거래 값 - 5000원 이상
AllowCoinPrice = 5000                           # 최소 코인 가격
feePercent = 0.9995                             # 수수료 퍼센트
isLive = True                                   # 실제 매수, 매도 여부
isKakao = True                                  # 실 제 카카오 메시지 수행 여부
isAutoChangeCoin = True                        # 자동으로 Coin 변경
########################

def init():
    global curCoinIdx, tickerlist
    if isKakao:
        kakaoControl.initKakao()       # 카카오 Module 초기화
        kakaoControl.refreshToken()
    tickerlist = list(upbitControl.get_ticker())        # ticker 리스터 획득
    print(tickerlist)
    curCoinIdx = 0                              # 현재 코인의 Index

# Log 저장 로직
def sendLogMessage():
    path = "../live/output.log"
    try:
        with open(path, 'r') as file:
            doc = file.read()
            if isKakao:
                kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'], doc)
        with open(path,'w') as file:
            file.write('')
    except Exception as e:
        addLog("[sendLogMessage] : " + e)
        print(e)

def readLog():
    path = "../live/output.log"
    try:
        with open(path, 'r') as file:
            doc = file.read()
            return doc
    except Exception as e:
        addLog("[readLog] : " + e)
        print(e)
        return None

# Log 추가 로직
def addLog(text):
    path = "../live/output.log"
    try:
        txt = readLog()
        with open(path, 'w') as file:
            file.write("{} {}".format(txt,"\n"+text))
    except Exception as e:
        addLog("[addLog] : " + e)
        print(e)

def nextCoin():
    global  curCoinIdx, tickerlist, targetCoin
    curCoinIdx = curCoinIdx + 1
    if curCoinIdx > len(tickerlist) - 1:
        curCoinIdx = 0
    targetCoin = tickerlist[curCoinIdx]

def logOutput(now, krw, targetCoin, unit, target_price, current_price):
    # 3.4 Log 저장 로직
    if now.strftime('%S') == '00':  # 분당 저장
        addLog("[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] KRW : " + str(krw) + ", Coin Name :" + str(
            targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
            target_price) + ", Current Price : " + str(current_price))

    # 하루 마감시 마지막 Log 전송
    if now.strftime('%H:%M:%S') == "08:59:59":
        sendLogMessage("KRW : " + str(krw) + ", Coin Name :" + str(targetCoin) + ", Unit : " + str(
            unit) + ", Target Price : " + str(target_price) + ", Current Price : " + str(
            current_price) + "\n------------")

    # 3.5 정시 정기 보고
    if now.strftime('%M') == '00' and now.strftime('%S') == '00':
        if isKakao:
            kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                         "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 상황 보고\nKRW : " + str(
                                             krw) + ", Coin Name :" + str(targetCoin) + ", Unit : " + str(
                                             unit) + ", Target Price : " + str(
                                             target_price) + ", Current Price : " + str(current_price))

def autoTradingTest():
    global tradeState, targetCoin, AllowCoinPrice, tickerlist

    """
    init()
    #sendLogMessage()
    now = datetime.datetime.now()
    krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
    unit = upbitControl.get_balance(upbitInst, targetCoin)
    #print("[" + now.strftime('%H:%M:%S') + "] 상황 보고\n현재 원화 : " + str(krw) + "\n코인 - " + targetCoin + " : " + str(unit))
    #kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'], "[" + now.strftime('%H:%M:%S') + "] 상황 보고\n현재 원화 : " + str(krw) + "\n코인 - " + targetCoin + " : " + str(unit))
    print(upbitControl.get_ticker())

    #start_time = upbitControl.get_start_time("KRW-BTC")  # 9:00
    #end_time = start_time + datetime.timedelta(days=1)  # 9:00 + 1일
    start_time = now - datetime.timedelta(seconds=1)
    end_time = start_time + datetime.timedelta(seconds=10)  # 9:00 + 1일
    #
    print(now)
    print(start_time)
    print(end_time)


    upbitControl.get_yesterday_ma5(targetCoin)
    print(targetCoin)
    """

    # Log 파일 테스트
    """
    path = "../live/output.log"
    # 1.초기화
    with open(path, 'w') as file:
        file.write("")

    txt = readLog()
    print(len(txt))
    # 2.첫 message
    addLog("매수 : 33444!!")
    txt = readLog()
    print(txt)

    addLog("매도 : 5554!!")
    txt = readLog()
    print(txt)
    

    """
    # 조회 수치 및 Log 값 테스트
    """
    now = datetime.datetime.now()
    krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인
    target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
    orderbook = pyupbit.get_orderbook(targetCoin)
    print(orderbook["orderbook_units"][0]["ask_price"])

    while True:
        now = datetime.datetime.now()
        if now.strftime('%S') == '00':  # 분당 저장
            addLog(
                "KRW : " + str(krw) + ", Coin Name :" + str(targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(target_price) + ", Current Price : " + str(current_price))
        print(now.strftime('%S'))
        time.sleep(1)
    """
    # 자동 매매 기능 테스트
    """
    while True:
        try:
            if tradeState == TradeState.ready:
                tradeState = TradeState.trading
                print(tradeState.value)
            now = datetime.datetime.now()
            print(now.strftime('%H:%M:%S'))
            print("min : ", now.strftime('%M'), "sceond" ,now.strftime('%S'))
            min = now.strftime('%M')
            sec = now.strftime('%S')
            if now.strftime('%M') == '02' and now.strftime('%S') == '00':
                print("same!!!!!")


            if start_time < now < end_time:
                if tradeState == TradeState.waiting:
                    tradeState = TradeState.trading
                    print(tradeState.value)
                    time.sleep(1)
                    continue
                #print(targetCoin)
                target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
                print("target : ", target_price, " coin : ", targetCoin)
                current_price = upbitControl.get_current_price(targetCoin)
                print(current_price)


                #if target_price < current_price:            # 목표값 < 현재값
                print(upbitControl.get_balance(upbitInst,ticker="KRW"))          # 보유 KRW
                print("all",upbitInst.get_amount('ALL'))                         # 총매수금액
                print(upbitControl.get_balance(upbitInst,ticker="KRW-BTC"))      # 비트코인 보유수량
                print(upbitControl.get_balance(upbitInst,ticker="KRW-XRP"))      # 리플 보유수량
                #print("원화 ", krw)
                    #if krw > 5000:  # 원화가 5000보다 크면
                print("111")
                btc = upbitControl.get_balance(upbitInst,targetCoin)
                print(btc)
            else:
                if tradeState == TradeState.waiting:
                    tradeState = TradeState.trading
                    print(tradeState.value)
                    time.sleep(1)
                    continue
                print("waitng")

        except Exception as e:
            print(e)
        time.sleep(1)
    """
    # Coin 변경 로직
    #"""
    tickerlist = list(upbitControl.get_ticker())
    # print(upbitControl.get_ticker())
    tickerlist = ["KRW-BTC", "KRW-ETH", "KRW-ETC"]
    curCoinIdx = 0
    targetCoin = tickerlist[curCoinIdx]
    while True:

        target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
        current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
        print(targetCoin + ", 목표가 : " + str(target_price) + ", 현재가 : " + str(current_price))
        curCoinIdx = curCoinIdx + 1
        if target_price < current_price:
            if curCoinIdx > len(tickerlist) - 1:
                global curCoinIndx
                curCoinIdx = 0


            if target_price > AllowCoinPrice:
                time.sleep(0.1)
                continue

            if target_price < current_price:  # 목표값 < 현재값
                print("매수")
        else:
            targetCoin = tickerlist[curCoinIdx]
        time.sleep(1)

    #"""
    # Log 저장 테스트
    """
    now = datetime.datetime.now()
    krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인
    target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
    orderbook = pyupbit.get_orderbook(targetCoin)
    print(orderbook["orderbook_units"][0]["ask_price"])

    while True:
        now = datetime.datetime.now()
        if now.strftime('%S') == '00':  # 분당 저장
            addLog(
                "KRW : " + str(krw) + ", Coin Name :" + str(targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(target_price) + ", Current Price : " + str(current_price))
        print(now.strftime('%S'))
        time.sleep(1)
    """

def autoTradingLive():
    global curCoinIdx, isAutoChangeCoin, targetCoin, tickerlist, trademode

    # 1. 초기화
    init()
    # 2. 트레이딩 시작 알림
    now = datetime.datetime.now()
    #if isKakao:
    #    kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] Bitcoin 트래이딩 시작!!\n" +str(trademode.value))

    # 3. 자동매매 시작
    #=== 변동성 돌파 전략 ====
    if trademode == TradeMode.break_out_range:
        while True:
            try:
                # 3.1 시간 설정 (현재 , 당일 시작, 명일 시작)
                now = datetime.datetime.now()                               # 현재 시간을 받아옴
                start_time = upbitControl.get_start_time(targetCoin)        # 당일 시작 시간 - 9:00
                end_time = start_time + datetime.timedelta(days=1)          # 명일 시작 시간 - 9:00 (+ 1일)
                target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
                current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                krw = upbitControl.get_balance(upbitInst, "KRW")            # 원화 조회
                unit = upbitControl.get_balance(upbitInst, targetCoin)      # 보유 코인

                # 3.2 매수 로직 -  당일 9:00 < 현재 < # 명일 8:59:45
                if start_time < now < end_time - datetime.timedelta(seconds=15):
                    if krw > tradeVolumeMin:  # 원화가 5000보다 크면
                        if target_price < current_price:  # 목표값 < 현재값
                            if isAutoChangeCoin == True:
                                if current_price > AllowCoinPrice:       # 허용 수치 보다 크다면
                                    nextCoin()
                                    logOutput(now, krw, targetCoin, unit, target_price, current_price)
                                    time.sleep(1)
                                    continue

                                if isLive:
                                    upbitInst.buy_market_order(targetCoin, krw * feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                                    addLog(
                                        "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매수 - KRW : " + str(
                                            krw) + ", Coin Name :" + str(
                                            targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                            target_price) + ", Current Price : " + str(current_price))
                                    if isKakao:
                                        kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매수!!!\n" + str(targetCoin) + " - " + str(5000 * feePercent))
                                else:
                                    print("매수 처리", targetCoin, krw * feePercent)
                        else:
                            if isAutoChangeCoin == True:
                                nextCoin()
                    else:       # 원화가 없으면 매수 모드에서는 아무것도 처리하지 않는다.
                        pass

                # 3.3 매도 로직 - 명일 8:59:46 ~ 9:00:00
                else:
                    if isLive:
                        if unit > 0:
                            upbitInst.sell_market_order(targetCoin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                            addLog(
                                "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매도 - KRW : " + str(krw) + ", Coin Name :" + str(
                                    targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                    target_price) + ", Current Price : " + str(current_price))
                            if isKakao:
                                kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매도!!!\n" + str(targetCoin) + " - " + str(unit))
                    else:
                        addLog(
                            "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매도 완료 - KRW : " + str(
                                krw) + ", Coin Name :" + str(
                                targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                target_price) + ", Current Price : " + str(current_price))

                logOutput(now,krw,targetCoin, unit, target_price, current_price)
            except Exception as e:
                print(e)
                addLog("[tradeLive] : " + e)
                if isKakao:
                    kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 에러발생!!!\nKRW : " + str(krw) + ", Coin Name :" + str(targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(target_price) + ", Current Price : " + str(current_price))
            time.sleep(1)

    # === 변동성 돌파 전략 + 이동 평균 ====
    elif trademode == TradeMode.break_out_range_and_ma5:    # 변동성 돌파 전략 + 전일 기준 5일 이동 평균값
        while True:
            try:
                # 3.1 시간 설정 (현재 , 당일 시작, 명일 시작)
                now = datetime.datetime.now()  # 현재 시간을 받아옴
                start_time = upbitControl.get_start_time(targetCoin)  # 당일 시작 시간 - 9:00
                end_time = start_time + datetime.timedelta(days=1)  # 명일 시작 시간 - 9:00 (+ 1일)
                target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
                current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                ma5 = upbitControl.get_yesterday_ma5(targetCoin)
                krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
                unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인

                # 3.2 매수 로직 -  당일 9:00 < 현재 < # 명일 8:59:55
                if start_time < now < end_time - datetime.timedelta(seconds=5):
                    if (current_price > target_price) and (current_price > ma5):  # 목표가 뿐만 아니라 이동평균과 현재가를 비교한다
                        if krw > tradeVolumeMin:  # 원화가 5000보다 크면
                            if isLive:
                                upbitInst.buy_market_order(targetCoin,krw * feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                                if isKakao:
                                    kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매수!!!\n" + str(targetCoin) + " - " + str(5000 * feePercent))
                            else:
                                print("매수 처리", targetCoin, krw * feePercent)
                    else:
                        if isAutoChangeCoin == True:
                            curCoinIdx = curCoinIdx + 1
                            if curCoinIdx > len(tickerlist) - 1:
                                curCoinIdx = 0
                            targetCoin = tickerlist[curCoinIdx]

                # 3.3 매도 로직 - 명일 8:59:56 ~ 9:00:00
                else:
                    if isLive:
                        upbitInst.sell_market_order(targetCoin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                        if isKakao:
                            kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                         "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매도!!!\n" + str(
                                                             targetCoin) + " - " + str(unit))
                    else:
                        print("매도 처리", targetCoin, unit)

                # 3.4 Log 저장 로직
                if now.strftime('%S') == '00':  # 분당 저장
                    addLog("[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] KRW : " + str(krw) + ", Coin Name :" + str(
                        targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                        target_price) + ", Current Price : " + str(current_price))

                # 하루 마감시 마지막 Log 전송
                if now.strftime('%H:%M:%S') == "08:59:59":
                    sendLogMessage("KRW : " + str(krw) + ", Coin Name :" + str(targetCoin) + ", Unit : " + str(
                        unit) + ", Target Price : " + str(target_price) + ", Current Price : " + str(
                        current_price) + "\n------------")

                # 3.5 정시 정기 보고
                if now.strftime('%M') == '00' and now.strftime('%S') == '00':
                    if isKakao:
                        kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                     "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 상황 보고\nKRW : " + str(
                                                         krw) + ", Coin Name :" + str(targetCoin) + ", Unit : " + str(
                                                         unit) + ", Target Price : " + str(
                                                         target_price) + ", Current Price : " + str(current_price))

            except Exception as e:
                print(e)
                addLog("[tradeLive] : " + e)
                if isKakao:
                    kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                 "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 에러발생!!!\nKRW : " + str(
                                                     krw) + ", Coin Name :" + str(targetCoin) + ", Unit : " + str(
                                                     unit) + ", Target Price : " + str(
                                                     target_price) + ", Current Price : " + str(current_price))
            time.sleep(1)
    # === 변동성 돌파 전략 + 이동 평균 ====
    elif trademode == TradeMode.break_out_range_and_down_sell:
        pass
    else:
        print("준비중")
        time.sleep(1)

upbitInst = upbitControl.create_instance()                            # Upbit instance

if isLive:
    autoTradingLive()
else:
    autoTradingTest()
