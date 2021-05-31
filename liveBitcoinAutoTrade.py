import time
import pyupbit
import datetime

# 로그인 정보
access = "cnEZzroCWQOx8yHfxdxQllffJlu2MqPTHNgJ3N3H"          # 본인 값으로 변경
secret = "BonpNve3xzmXJTOeuxM1pgLtiodYixgl0ZXF1sBb"          # 본인 값으로 변경

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

# 잔고 조회
print(upbit.get_balance("KRW-SBD"))     # KRW-SBD 조회
print(upbit.get_balance("KRW-ETH"))     # KRW-ETH 조회
print(upbit.get_balance("KRW"))         # 보유 현금 조회

# 코인 배팅 설정
krw = get_balance("KRW")            # 원화 조회

krw_eth = krw * 0.5     #이더리움
krw_xrp = krw * 0.2     #리플
krw_etc = krw * 0.2     #이더리움 클래식
krw_doge = krw * 0.05     #도지코인
krw_sbd = krw * 0.05     #스팀달러

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()                       # 현재시간을 받아옴 
        start_time = get_start_time("KRW-ETH")              #9:00
        end_time = start_time + datetime.timedelta(days=1)  #9:00 + 1일

        # 매수 로직 -  9:00 < 현재 < #8:59:50
        if start_time < now < end_time - datetime.timedelta(seconds=10):
            #1.ETH
            target_price_eth = get_target_price("KRW-ETH", 0.4)     #목표값 설정 
            current_price_eth = get_current_price("KRW-ETH")        # 현재 값
            if target_price_eth < current_price_eth:        # 목표값 < 현재값
                if krw_eth > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-ETH", krw_eth*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
            
            #2.XRP
            target_price_xrp = get_target_price("KRW-XRP", 0.4)     #목표값 설정 
            current_price_xrp = get_current_price("KRW-XRP")        # 현재 값
            if target_price_xrp < current_price_xrp:        # 목표값 < 현재값
                if krw_xrp > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-XRP", krw_xrp*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정

            #3.ETC
            target_price_etc = get_target_price("KRW-ETC", 0.4)     #목표값 설정 
            current_price_etc = get_current_price("KRW-ETC")        # 현재 값
            if target_price_etc < current_price_etc:        # 목표값 < 현재값
                if krw_etc > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-ETC", krw_etc*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정        

            #4.DOGE
            target_price_doge = get_target_price("KRW-DOGE", 0.4)     #목표값 설정 
            current_price_doge = get_current_price("KRW-DOGE")        # 현재 값
            if target_price_doge < current_price_doge:        # 목표값 < 현재값
                if krw_doge > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-DOGE", krw_doge*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정        

            #5.SBD
            target_price_sbd = get_target_price("KRW-SBD", 0.4)     #목표값 설정 
            current_price_sbd = get_current_price("KRW-SBD")        # 현재 값
            if target_price_sbd < current_price_sbd:        # 목표값 < 현재값
                if krw_sbd > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-SBD", krw_sbd*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정        

        # 매도 로직 - 8:59:51 ~ 9:00:00
        else:
            ehc = get_balance("KRW-ETH")
            if ehc > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-ETH", ehc*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료
            
            xrp = get_balance("KRW-XRP")
            if xrp > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-XRP", xrp*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료

            etc = get_balance("KRW-ETC")
            if etc > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-ETC", etc*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료

            doge = get_balance("KRW-DOGE")
            if doge > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-DOGE", doge*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료

            sbd = get_balance("KRW-SBD")
            if sbd > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-SBD", sbd*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료

        time.sleep(1)
    except Exception as e:
        print(e)
        time.sleep(1)