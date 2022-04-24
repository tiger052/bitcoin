import pyupbit
import datetime
import time
import kakaoControl
import upbitControl
from enum import Enum
import os.path

class TradeState(Enum):
    initialize = "init"                         # 초기화 단계 : Ticer 정보 및 현재 Coin 상태를 설정 및 초기화 한다.
    ready = "ready"                             # 준비 단계 : 매수 전 데이터를 수집하는 단계 (변동성 + 하락 + 효율 )
    trading = "trading"                         # 트레이딩 단계 : 매수를 시도하는 단계
    complete_trade = "complete_trade"           # 트레이드 한 상태 : 매수 처리가 완료된 상태 (변동성)
    drop_check = "drop_check"                   # 하락 체크 상태 : 매수한 코인이 하락 하는지 체크 (변동성 + 하락)
    selling = "selling"                         # 매도 상태 : 매도를 시도하는 단계
    complete_sell = "complete_sell"             # 매도 된 상태 : 매도 처리가 완료된 상태
    waiting = "waiting"                         # 대기 중

class ProcessState(Enum):
    processing = "processing"                   # 처리중
    complete = "waiting"                        # 완료

class TradeMode(Enum):
    break_out_range = "변동성 돌파 전략"                                    # 변동성 돌파 전략
    break_out_range_and_ma5 = "변동성 돌파 + 5일 이동 평균 전략"              # 변동성 돌파 전략 + 전일 기준 5일 이동 평균값
    break_out_range_and_down_sell = "변동성 돌파 전략 + 하락시 매도 전략"      # 매수 : 변동성 돌파 전략 , 매도 : 일정 기준 하락시
    break_out_range_and_asking_buy_down_sell = "변동성 돌파 전략 + 호가 비교 + 하락시 매도 전략"  # 매수 : 변동성 돌파 전략 , 매도 : 일정 기준 하락시
    reading = "준비중"

usedCoindic = {}                                # 매수시 Dictionary에 저장하여 관리 (매도시 사용)
tickerlist = []                                 # Tickers 전체 list
coinlist = []                                   # 거래할 코인 list (코인 최소 가격으로 걸러진 금액)
buy_price = 0                                   # 매수 시 금액
sell_price = 0                                  # 판매 하기 위한 금액
max_price = 0                                   # 매수 후 최고 가격
########################
## Trading Setting #####
########################
#-- 트레이드 셋팅
trademode = TradeMode.break_out_range_and_asking_buy_down_sell           # 트레이드 모드 설정
targetCoin = "KRW-XRP"                          # 트레이드 할 Coin
tradeState = TradeState.initialize              # 트레이드 상태
processState = ProcessState.complete            # 처리 상태

#-- 트레이딩 수치값
targetPercent = 0.5                             # 변동성 돌파 목표치 비율
targetSellPercent = 0.01                        # 판매 목표 치 비율( target price 에 해당 비율의 곱)
tradeVolumeMin = 5000                           # 최소 거래 값 - 5000원 이상
AllowCoinPrice = 5000                           # 최소 코인 가격
feePercent = 0.9995                             # 수수료 퍼센트
tradeCheckTime = 0.2                            # 트레이드 모드시 해당 수치 마다 체크

#-- 호가 비교 전략 정보
priceComparisonsMax = 2                         # 호가 비교 횟수
gravityDepth = 0.1                              # 호가 비교시 단계별 depth 값
bid_buy_ratio = 5                               # 호가 매수 비율 (해당 비율이 넘을시 매수)
isGravity = True                                # 호가 비교시 비중을 줄지 여부


#-- 시스템설정
isLive = True                                   # 실제 매수, 매도 여부
isKakao = True                                  # 실 제 카카오 메시지 수행 여부
isAutoChangeCoin = True                         # 자동으로 Coin 변경
########################

#초기화 처리
def init():
    addLog("[TradeState - init] - Trade Mode : {} ".format(trademode.value))
    global tradeState, upbitInst, processState
    processState = ProcessState.processing
    if isKakao:
        kakaoControl.initKakao()                # 카카오 Module 초기화
        kakaoControl.refreshToken()

    upbitInst = upbitControl.create_instance()  # Upbit instance

    processState = ProcessState.complete
    tradeState = TradeState.ready
    addLog("\n[TradeState - ready]")

#셋팅 정보 초기화
def reset():
    global curCoinIdx, tradeState, tickerlist, coinlist, processState, sell_price
    processState = ProcessState.processing

    curCoinIdx = 0  # 현재 코인의 Index
    sell_price = 0  # 매수 가
    tickerlist.clear()
    coinlist.clear()
    usedCoindic.clear()

    checkCoinInfo()

    processState = ProcessState.complete
    tradeState = TradeState.trading
    addLog("\n[TradeState - Trading]")

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
        addLog("[sendLogMessage] : {}".format(e))
        print(e)

def readLog():
    path = "../live/output.log"
    try:
        with open(path, 'r') as file:
            doc = file.read()
            return doc
    except Exception as e:
        addLog("[readLog] : {}".format(e))
        print(e)
        return None

# Log 추가 로직
def addLog(text):
    path = "../live/output.log"
    try:
        txt = readLog()
        with open(path, 'w') as file:
            file.write("{} {}".format(txt,"\n"+text))
        print(text)
    except Exception as e:
        addLog("[addLog] : " + e)
        print(e)

def nextCoin():
    global  curCoinIdx, coinlist, targetCoin
    curCoinIdx = curCoinIdx + 1
    if curCoinIdx > len(coinlist) - 1:
        curCoinIdx = 0
    targetCoin = coinlist[curCoinIdx]

def checkCoinInfo():
    global tickerlist, coinlist, usedCoindic, targetCoin
    print("====Check Coin Info Start!====")
    tickerlist = list(upbitControl.get_ticker())        # ticker 리스터 획득
    print(">> ticker list - {}, {}".format(len(tickerlist), tickerlist))

    for ticker in tickerlist:
        curPrice = upbitControl.get_current_price(ticker)
        balance = upbitControl.get_balance(upbitInst, ticker)
        if balance > 0:
            if curPrice * balance > 5000:
                usedCoindic[ticker] = balance
                targetCoin = ticker
        if 1 < curPrice < 5000:                 # 소수점 이하 coin 은 배제한다
            coinlist.append(ticker)
    print(">> used coin dic - size : {}, dic : {} ".format(len(usedCoindic), usedCoindic))
    print(">> real coin list - size : {}, list : {}".format(len(coinlist), coinlist))
    print(">> current Target Coin - {}".format(targetCoin))
    print("====Complete Check Coin Info====")

# 호가 비교
def priceComparisons(ticker):
    global priceComparisonsMax, gravityDepth, bid_buy_ratio, isGravity, sell_price

    compareList = []
    totalBid_point = 0  # 전체 매수 호가
    totalAsk_point = 0  # 전체 매도 호가
    gravity = 1 + priceComparisonsMax * gravityDepth
    result = False

    try:
        datalist = list(upbitControl.get_current_orderbook(ticker))

        # 비교 list 생성
        for i in range(priceComparisonsMax):
            compareList.append(datalist[i])

        #print(compareList)

        # 매수 점수
        for data in compareList:
            bid_price = data['bid_price']
            bid_size = data['bid_size']
            ask_price = data['ask_price']
            ask_size = data['ask_size']
            totalBid_point = (totalBid_point + bid_price * bid_size) * gravity
            totalAsk_point = (totalAsk_point + ask_price * ask_size) * gravity
            gravity = gravity - gravityDepth

        resultRatio = totalBid_point / totalAsk_point

        if (resultRatio > bid_buy_ratio):
            result = True
        now = datetime.datetime.now()
        print(">> [{}] 호가 비교 구문 coin : {}, 매수 : {}, 매도 : {}, ratio : {}, 매수 처리 결과 : {}".format(now.strftime('%Y-%m-%d %H:%M:%S'), ticker, round(totalBid_point, 2), round(totalAsk_point, 2), resultRatio, result))

    except Exception as e:
        print(e)

    return result

def logOutput(now, krw, targetCoin, unit, target_price, current_price):
    # 3.4 Log 저장 로직
    if now.strftime('%S') == '00':  # 분당 저장
        addLog(">> [{}] 분당 보고 - STATE : {},  KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(now.strftime('%Y-%m-%d %H:%M:%S'),tradeState.value, krw, targetCoin, unit, target_price, current_price))

    # 하루 마감시 마지막 Log 전송
    if now.strftime('%H:%M:%S') == "08:59:59":
        sendLogMessage("[{}] 하루 마감 보고 - KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}\n----------".format(now.strftime('%Y-%m-%d %H:%M:%S'), krw, targetCoin, unit, target_price, current_price))

    # 3.5 정시 정기 보고
    if now.strftime('%M') == '00' and now.strftime('%S') == '00':
        if isKakao:
            kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[{}] 하루 마감 보고 - KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}\n----------".format(now.strftime('%Y-%m-%d %H:%M:%S'), krw, targetCoin, unit, target_price, current_price))

def autoTradingTest():
    global tradeState, targetCoin, curCoinIdx, AllowCoinPrice, tickerlist, usedCoindic
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
    """
    #tickerlist = list(upbitControl.get_ticker())
    #print(upbitControl.get_ticker())
    coinlist = ["KRW-BTC", "KRW-ETH", "KRW-ETC"]
    curCoinIdx = 0
    targetCoin = coinlist[curCoinIdx]
    usedCoindic["KRW-BTC"] = 5.5
    usedCoindic["KRW-ETH"] = 3.5
    init()
    print(usedCoindic)
    for data in usedCoindic:
        print(data, usedCoindic[data])
    usedCoindic.pop("KRW-BTC")
    #usedTickerdic.clear()

    print(usedCoindic)

    current_price = upbitControl.get_current_price("KRW-BTC")  # 현재 값
    unit = upbitControl.get_balance(upbitInst, "KRW-BTC")  # 보유 코인
    print(current_price, unit, current_price * unit)
    if current_price * unit > 5000:
        print("sell")
    else:
        print("cant sell")
    while True:

        target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
        current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
        print(targetCoin + ", 목표가 : " + str(target_price) + ", 현재가 : " + str(current_price))
        curCoinIdx = curCoinIdx + 1
        if curCoinIdx > len(coinlist) - 1:
            curCoinIdx = 0

        if target_price < current_price:
            if target_price > AllowCoinPrice:
                time.sleep(0.1)
                continue

            if target_price < current_price:  # 목표값 < 현재값
                print("매수")
        else:
            print(len(coinlist))
            targetCoin = coinlist[curCoinIdx]
        time.sleep(1)

    """
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
    global tradeState, trademode, targetCoin, usedCoindic, processState, isAutoChangeCoin, targetSellPercent, buy_price, max_price, sell_price

    # === 변동성 돌파 전략 ====
    if trademode == TradeMode.break_out_range:
        while True:
            if processState == ProcessState.processing:
                time.sleep(1)
                continue

            # 3.1 시간 설정 (현재 , 당일 시작, 명일 시작)
            now = datetime.datetime.now()  # 현재 시간을 받아옴
            start_time = upbitControl.get_start_time(targetCoin)  # 당일 시작 시간 - 9:00
            end_time = start_time + datetime.timedelta(days=1)  # 명일 시작 시간 - 9:00 (+ 1일)

            try:
                if tradeState == TradeState.initialize:     # 1. 초기화
                    init()
                elif tradeState == TradeState.ready:        # 2. 설정 초기화
                    reset()
                elif tradeState == TradeState.trading:      # 3. 트레이딩

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
                                    usedCoindic[targetCoin] = current_price                 # 매수 dic에 저장
                                    addLog(
                                        "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매수 - KRW : " + str(
                                            krw) + ", Coin Name :" + str(
                                            targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                            target_price) + ", Current Price : " + str(current_price))
                                    if isKakao:
                                        kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매수!!!\n" + str(targetCoin) + " - " + str(5000 * feePercent))

                                    tradeState = TradeState.complete_trade
                                    addLog("\n[TradeState - complete_trade]")
                                else:
                                    print("매수 처리", targetCoin, krw * feePercent)
                            else:
                                if isAutoChangeCoin == True:
                                    nextCoin()
                        else:       # 원화가 없으면 매수 모드에서는 아무것도 처리하지 않는다.
                            tradeState = TradeState.complete_trade
                            addLog("\n[TradeState - complete_trade]")
                        logOutput(now, krw, targetCoin, unit, target_price, current_price)
                    else:
                        tradeState = TradeState.selling
                        addLog("\n[TradeState - complete_trade]")

                elif tradeState == TradeState.complete_trade:
                    # 구매여부 확인 로직
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인
                    if unit > 0:
                        tradeState = TradeState.waiting
                        addLog("\n[TradeState - waiting] " + str(targetCoin) + " : " + str(unit))

                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        tradeState = TradeState.selling
                        addLog("\n[TradeState - selling]")

                elif tradeState == TradeState.waiting:
                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        tradeState = TradeState.selling
                        addLog("\n[TradeState - selling]")

                elif tradeState == TradeState.selling:
                    # 3.3 매도 로직 - 명일 8:59:46 ~ 9:00:00
                    target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
                    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                    krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인

                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        if len(usedCoindic) > 0:
                            for coin in usedCoindic:
                                current_price = upbitControl.get_current_price(coin)  # 현재 값
                                unit = upbitControl.get_balance(upbitInst, coin)  # 보유 코인
                                if current_price * unit > 5000:
                                    upbitInst.sell_market_order(coin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                                    usedCoindic.pop(coin)
                                    addLog(
                                        "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매도 - KRW : " + str(
                                            krw) + ", Coin Name :" + str(
                                            targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                            target_price) + ", Current Price : " + str(current_price))
                                    if isKakao:
                                        kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                                     "[" + now.strftime(
                                                                         '%Y-%m-%d %H:%M:%S') + "] 매도!!!\n" + str(
                                                                         targetCoin) + " - " + str(unit))
                        else:
                            tradeState = TradeState.complete_sell
                            addLog("\n[TradeState - complete_sell]")
                            addLog(
                                "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매도 완료 - KRW : " + str(
                                    krw) + ", Coin Name :" + str(
                                    targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                    target_price) + ", Current Price : " + str(current_price))

                        logOutput(now, krw, targetCoin, unit, target_price, current_price)

                        if now.strftime('%H:%M:%S') == "08:59:59" and now.strftime('%H:%M:%S') == "08:59:58":
                            tradeState = TradeState.ready
                            addLog("\n[TradeState - ready]")

                elif tradeState == TradeState.complete_sell:
                    if now.strftime('%H:%M:%S') == "08:59:59" and now.strftime('%H:%M:%S') == "08:59:58":
                        tradeState = TradeState.ready
                        addLog("\n[TradeState - ready]")

            except Exception as e:
                print(e)
            time.sleep(1)
    # === 변동성 돌파 전략 + 이동 평균 ====
    elif trademode == TradeMode.break_out_range_and_ma5:  # 변동성 돌파 전략 + 전일 기준 5일 이동 평균값
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
                                upbitInst.buy_market_order(targetCoin,
                                                           krw * feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                                if isKakao:
                                    kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                                 "[" + now.strftime(
                                                                     '%Y-%m-%d %H:%M:%S') + "] 매수!!!\n" + str(
                                                                     targetCoin) + " - " + str(5000 * feePercent))
                            else:
                                print("매수 처리", targetCoin, krw * feePercent)
                    else:
                        if isAutoChangeCoin == True:
                            curCoinIdx = curCoinIdx + 1
                            if curCoinIdx > len(coinlist) - 1:
                                curCoinIdx = 0
                            targetCoin = coinlist[curCoinIdx]

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
        while True:
            if processState == ProcessState.processing:
                time.sleep(1)
                continue

            # 3.1 시간 설정 (현재 , 당일 시작, 명일 시작)
            now = datetime.datetime.now()  # 현재 시간을 받아옴
            start_time = upbitControl.get_start_time(targetCoin)  # 당일 시작 시간 - 9:00
            end_time = start_time + datetime.timedelta(days=1)  # 명일 시작 시간 - 9:00 (+ 1일)

            try:
                if tradeState == TradeState.initialize:  # 1. 초기화
                    init()
                elif tradeState == TradeState.ready:  # 2. 설정 초기화
                    reset()
                elif tradeState == TradeState.trading:  # 3. 트레이딩
                    target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
                    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                    krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인

                    # 3.2 매수 로직 -  당일 9:00 < 현재 < # 명일 8:59:45
                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        if krw > tradeVolumeMin:  # 원화가 5000보다 크면

                            if target_price < current_price:  # 목표값 < 현재값
                                if isAutoChangeCoin == True:
                                    if current_price > AllowCoinPrice:  # 허용 수치 보다 크다면
                                        nextCoin()
                                        logOutput(now, krw, targetCoin, unit, target_price, current_price)
                                        time.sleep(1)
                                        continue

                                if isLive:
                                    upbitInst.buy_market_order(targetCoin,
                                                               krw * feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                                    usedCoindic[targetCoin] = current_price  # 매수 dic에 저장
                                    buy_price = current_price               # 매수 가
                                    max_price = current_price
                                    addLog(
                                        "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매수 - KRW : " + str(
                                            krw) + ", Coin Name :" + str(
                                            targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                            target_price) + ", Current Price : " + str(current_price))
                                    if isKakao:
                                        kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                                     "[" + now.strftime(
                                                                         '%Y-%m-%d %H:%M:%S') + "] 매수!!!\n" + str(
                                                                         targetCoin) + " - " + str(5000 * feePercent))

                                    tradeState = TradeState.complete_trade
                                    addLog("[TradeState - complete_trade]")
                                else:
                                    print("매수 처리", targetCoin, krw * feePercent)
                            else:
                                if isAutoChangeCoin == True:
                                    nextCoin()
                        else:  # 원화가 없으면 매수 모드에서는 아무것도 처리하지 않는다.
                            tradeState = TradeState.complete_trade
                            addLog("[TradeState - complete_trade]")
                        logOutput(now, krw, targetCoin, unit, target_price, current_price)
                    else:
                        tradeState = TradeState.selling
                        addLog("[TradeState - complete_trade]")

                elif tradeState == TradeState.complete_trade:
                    # 구매여부 확인 로직
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인
                    if unit > 0:
                        tradeState = TradeState.drop_check
                        addLog("[TradeState - drop_check] " + str(targetCoin) + " : " + str(unit))

                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        tradeState = TradeState.selling
                        addLog("[TradeState - drop_check]")

                elif tradeState == TradeState.drop_check:
                    sell_price = max_price - target_price * targetSellPercent
                    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                    if start_time < now < end_time - datetime.timedelta(seconds=15):

                        if max_price < current_price:           # 최고 가격을 갱신했다면
                            max_price = current_price
                            sell_price = max_price - target_price * targetSellPercent
                        if buy_price == 0:
                            buy_price = current_price
                        start_price = upbitControl.get_start_price(targetCoin)
                        currentRatio = (current_price / start_price - 1 ) * 100
                        earinigRatio = (current_price / buy_price - 1) * 100
                        print("하락장 체크 구문 -  coin : " + str(targetCoin) + ", 최고가 :" + str(max_price) + ", 구매가 :" + str(buy_price) + ", 현재가 :" + str(current_price) + ", 시가 :" + str(start_price) + ", 판매 목표가 :" + str(sell_price) + ", 목표가 :" + str(target_price) + ", 진행률 :  " + str(round(currentRatio,2)) + ",  수익률 : " + str(round(earinigRatio,2)))
                        if current_price < sell_price:  # 판매 공식 : 현재가가 최고가 - 갭 수치 이하로 내려갈때 매도
                            if len(usedCoindic) > 0:
                                for coin in usedCoindic:
                                    current_price = upbitControl.get_current_price(coin)  # 현재 값
                                    unit = upbitControl.get_balance(upbitInst, coin)  # 보유 코인
                                    if current_price * unit > 5000:
                                        upbitInst.sell_market_order(coin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                                        usedCoindic.pop(coin)
                                        addLog(
                                            "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 하락 감지 매도 - KRW : " + str(krw) + ", Coin :" + str(targetCoin) + ", 최고가 :" + str(max_price) + ", 구매가 :" + str(buy_price) + ", 현재가 :" + str(current_price) + ", 시가 :" + str(start_price) + ", 판매 목표가 :" + str(sell_price) + ", 목표가 :" + str(target_price) + ", 진행률 :  " + str(round(currentRatio,2)) + ",  수익률 : " + str(round(earinigRatio,2)))
                                        if isKakao:
                                            kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 하락 감지 매도!!!\n" + str(targetCoin) + " - " + str(unit))
                            nextCoin()
                            tradeState = TradeState.trading
                            addLog("[TradeState - trading]")
                    else:
                        tradeState = TradeState.selling
                        addLog("[TradeState - selling]")
                elif tradeState == TradeState.waiting:
                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        tradeState = TradeState.selling
                        addLog("[TradeState - selling]")

                elif tradeState == TradeState.selling:
                    # 3.3 매도 로직 - 명일 8:59:46 ~ 9:00:00
                    target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
                    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                    krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인

                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        if len(usedCoindic) > 0:
                            for coin in usedCoindic:
                                current_price = upbitControl.get_current_price(coin)  # 현재 값
                                unit = upbitControl.get_balance(upbitInst, coin)  # 보유 코인
                                if current_price * unit > 5000:
                                    upbitInst.sell_market_order(coin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                                    usedCoindic.pop(coin)
                                    addLog(
                                        "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매도 - KRW : " + str(
                                            krw) + ", Coin Name :" + str(
                                            targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                            target_price) + ", Current Price : " + str(current_price))
                                    if isKakao:
                                        kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                                     "[" + now.strftime(
                                                                         '%Y-%m-%d %H:%M:%S') + "] 매도!!!\n" + str(
                                                                         targetCoin) + " - " + str(unit))
                        else:
                            tradeState = TradeState.complete_sell
                            addLog("[TradeState - complete_sell]")
                            addLog(
                                "[" + now.strftime('%Y-%m-%d %H:%M:%S') + "] 매도 완료 - KRW : " + str(
                                    krw) + ", Coin Name :" + str(
                                    targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                    target_price) + ", Current Price : " + str(current_price))

                        logOutput(now, krw, targetCoin, unit, target_price, current_price)

                        if now.strftime('%H:%M:%S') == "08:59:59" or now.strftime('%H:%M:%S') == "08:59:58":
                            tradeState = TradeState.ready
                            addLog("[TradeState - ready]")

                elif tradeState == TradeState.complete_sell:
                    if now.strftime('%H:%M:%S') == "08:59:59" or now.strftime('%H:%M:%S') == "08:59:58":
                        tradeState = TradeState.ready
                        addLog("[TradeState - ready]")

            except Exception as e:
                print(e)
            time.sleep(1)
    # === 변동성 돌파 전략 + 호가 비교 + 하락시 매도 전략 ====
    elif trademode == TradeMode.break_out_range_and_asking_buy_down_sell:
        while True:
            if processState == ProcessState.processing:
                time.sleep(1)
                continue

            # 3.1 시간 설정 (현재 , 당일 시작, 명일 시작)
            now = datetime.datetime.now()  # 현재 시간을 받아옴
            start_time = upbitControl.get_start_time(targetCoin)  # 당일 시작 시간 - 9:00
            end_time = start_time + datetime.timedelta(days=1)  # 명일 시작 시간 - 9:00 (+ 1일)

            try:
                if tradeState == TradeState.initialize:  # 1. 초기화
                    init()
                elif tradeState == TradeState.ready:  # 2. 설정 초기화
                    reset()
                elif tradeState == TradeState.trading:  # 3. 트레이딩
                    target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
                    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                    krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인

                    # 3.2 매수 로직 -  당일 9:00 < 현재 < # 명일 8:59:45
                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        if krw > tradeVolumeMin:  # 원화가 5000보다 크면
                            print(">> [{}] 가격 비교 구문 coin : {}, 현재가 : {}, 목표가: {}, 가격 비격 결과 : {}".format(now.strftime('%Y-%m-%d %H:%M:%S'), targetCoin, round(current_price, 2),round(target_price, 2), target_price < current_price))
                            if target_price < current_price:  # 목표값 < 현재값
                                if isAutoChangeCoin == True:
                                    if current_price > AllowCoinPrice:  # 허용 수치 보다 크다면
                                        nextCoin()
                                        logOutput(now, krw, targetCoin, unit, target_price, current_price)
                                        time.sleep(1)
                                        continue
                                # 실제 매수 로직
                                comparisonsResult = priceComparisons(targetCoin)
                                if comparisonsResult == True:
                                    upbitInst.buy_market_order(targetCoin,
                                                               krw * feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                                    usedCoindic[targetCoin] = current_price  # 매수 dic에 저장
                                    buy_price = current_price  # 매수 가
                                    max_price = current_price
                                    addLog(">> [{}] 매수 - KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(now.strftime('%Y-%m-%d %H:%M:%S'), krw, targetCoin, unit, target_price, current_price))
                                    if isKakao:
                                        kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],"[{}] 매수 - KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(now.strftime('%Y-%m-%d %H:%M:%S'), krw, targetCoin, unit, target_price, current_price))

                                    tradeState = TradeState.complete_trade
                                    addLog("\n[TradeState - complete_trade]")
                                else:
                                    nextCoin()
                                    logOutput(now, krw, targetCoin, unit, target_price, current_price)
                                    time.sleep(1)
                                    continue
                            else:
                                if isAutoChangeCoin == True:
                                    nextCoin()
                                if not tradeCheckTime == 1:
                                    time.sleep(tradeCheckTime)
                                    continue
                        else:  # 원화가 없으면 매수 모드에서는 아무것도 처리하지 않는다.
                            tradeState = TradeState.complete_trade
                            addLog("\n[TradeState - complete_trade]")
                        logOutput(now, krw, targetCoin, unit, target_price, current_price)
                    else:
                        tradeState = TradeState.selling
                        addLog("\n[TradeState - complete_trade]")

                elif tradeState == TradeState.complete_trade:
                    # 구매여부 확인 로직
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인
                    if unit > 0:
                        tradeState = TradeState.drop_check
                        addLog("\n[TradeState - drop_check] " + str(targetCoin) + " : " + str(unit))

                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        tradeState = TradeState.selling
                        addLog("\n[TradeState - drop_check]")

                elif tradeState == TradeState.drop_check:
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인
                    sell_price = max_price - target_price * targetSellPercent
                    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        if unit == 0:       # 외부에서 강제 판매 한 상황
                            addLog(">> [{}] 하락장 체크 중 외부 매도 감지 !!! - coin : {}".format(now.strftime('%Y-%m-%d %H:%M:%S'), targetCoin))
                            nextCoin()
                            tradeState = TradeState.ready
                            addLog("\n[TradeState - ready]")
                        if max_price < current_price:  # 최고 가격을 갱신했다면
                            max_price = current_price
                            sell_price = max_price - target_price * targetSellPercent
                        if buy_price == 0:
                            buy_price = current_price - current_price * 0.01
                        start_price = upbitControl.get_start_price(targetCoin)
                        currentRatio = (current_price / start_price - 1) * 100
                        earinigRatio = (current_price / buy_price - 1) * 100
                        margin = current_price - buy_price
                        print(">> [{}] 하락장 체크 구문 -  coin : {}, 최고가 : {}, 구매가 : {}, 현재가 : {}, 시가 : {}, 판매 목표가 : {}, 구입 목표가 : {}, 진행된 비율 : {}, 수익율 : {}, 마진 : {}".format(now.strftime('%Y-%m-%d %H:%M:%S'), targetCoin, max_price, buy_price, current_price, start_price, sell_price, target_price, round(currentRatio, 2), round(earinigRatio, 2), round(margin,2)))
                        if current_price < sell_price:  # 판매 공식 : 현재가가 최고가 - 갭 수치 이하로 내려갈때 매도
                            if len(usedCoindic) > 0:
                                for coin in usedCoindic:
                                    current_price = upbitControl.get_current_price(coin)  # 현재 값
                                    unit = upbitControl.get_balance(upbitInst, coin)  # 보유 코인
                                    if current_price * unit > 5000:
                                        upbitInst.sell_market_order(coin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                                        usedCoindic.pop(coin)

                                        addLog(">> [{}] 하락 감지 매도 - KRW : {}, coin : {}, 최고가 : {}, 구매가 : {}, 현재가 : {}, 시가 : {}, 판매 목표가 : {}, 구입 목표가 : {}, 진행된 비율 : {}, 수익율 : {}, 마진 : {}".format(now.strftime('%Y-%m-%d %H:%M:%S'), krw, targetCoin, max_price, buy_price,current_price, start_price, sell_price, target_price, round(currentRatio, 2), round(earinigRatio, 2), round(margin,2)))
                                        nextCoin()
                                        tradeState = TradeState.trading
                                        addLog("\n[TradeState - trading]")

                                        if isKakao:
                                            kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                                         "[{}] 하락 감지 매도 - KRW : {}, coin : {}, 최고가 : {}, 구매가 : {}, 현재가 : {}, 시가 : {}, 판매 목표가 : {}, 구입 목표가 : {}, 진행된 비율 : {}, 수익율 : {}, 마진 : {}".format(
                                                                             now.strftime('%Y-%m-%d %H:%M:%S'), krw,
                                                                             targetCoin, max_price, buy_price,
                                                                             current_price, start_price, sell_price,
                                                                             target_price, round(currentRatio, 2),
                                                                             round(earinigRatio, 2), round(margin, 2)))
                    else:
                        tradeState = TradeState.selling
                        addLog("\n[TradeState - selling]")
                elif tradeState == TradeState.waiting:
                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        tradeState = TradeState.selling
                        addLog("\n[TradeState - selling]")

                elif tradeState == TradeState.selling:
                    # 3.3 매도 로직 - 명일 8:59:46 ~ 9:00:00
                    target_price = upbitControl.get_target_price(targetCoin, targetPercent)  # 목표값 설정
                    current_price = upbitControl.get_current_price(targetCoin)  # 현재 값
                    krw = upbitControl.get_balance(upbitInst, "KRW")  # 원화 조회
                    unit = upbitControl.get_balance(upbitInst, targetCoin)  # 보유 코인

                    if start_time < now < end_time - datetime.timedelta(seconds=15):
                        pass
                    else:
                        if len(usedCoindic) > 0:
                            for coin in usedCoindic:
                                current_price = upbitControl.get_current_price(coin)  # 현재 값
                                unit = upbitControl.get_balance(upbitInst, coin)  # 보유 코인
                                if current_price * unit > 5000:
                                    upbitInst.sell_market_order(coin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                                    usedCoindic.pop(coin)
                                    addLog(">> [{}] 매도 - KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {} ".format(now.strftime('%Y-%m-%d %H:%M:%S'), krw, targetCoin, unit, target_price, current_price))
                                    if isKakao:
                                        kakaoControl.sendToMeMessage(kakaoControl.dic_apiData['frind_uuid'],
                                                                     "[{}] 매도 - KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {} ".format(
                                                                         now.strftime('%Y-%m-%d %H:%M:%S'), krw,
                                                                         targetCoin, unit, target_price, current_price))
                        else:
                            tradeState = TradeState.complete_sell
                            addLog(">> [{}] 매도 완료 - KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {} ".format(now.strftime('%Y-%m-%d %H:%M:%S'), krw, targetCoin, unit, target_price, current_price))
                            addLog("\n[TradeState - complete_sell]")
                        logOutput(now, krw, targetCoin, unit, target_price, current_price)

                        if now.strftime('%H:%M:%S') == "08:59:59" or now.strftime('%H:%M:%S') == "08:59:58":
                            tradeState = TradeState.ready
                            addLog("\n[TradeState - ready]")

                elif tradeState == TradeState.complete_sell:
                    if now.strftime('%H:%M:%S') == "08:59:59" or now.strftime('%H:%M:%S') == "08:59:58":
                        tradeState = TradeState.ready
                        addLog("\n[TradeState - ready]")

            except Exception as e:
                print(e)
            time.sleep(1)
    else:
        print("준비중")
        time.sleep(1)

now = datetime.datetime.now()
print("\n[{}] J1 Auto Bitcoin Start !!!!\n".format(now.strftime('%Y-%m-%d %H:%M:%S')))

if isLive:
    autoTradingLive()
#else:
 #   autoTradingTest()
