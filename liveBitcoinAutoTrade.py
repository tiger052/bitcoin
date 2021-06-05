# -*- coding: utf-8 -*-

import time
import pyupbit
import datetime
import requests

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

# 잔고 조회
def show_current_state():
    send_message("Current State")
    send_message('Current KRW : '+ str(upbit.get_balance("KRW")))         # 보유 현금 조회
    send_message('Current ETH : '+ str(upbit.get_balance("KRW-ETH")))     # KRW-ETH 조회
    send_message('Current ETC : '+ str(upbit.get_balance("KRW-ETC")))     # KRW-XRP 조회
    send_message('Current DOGE: '+ str(upbit.get_balance("KRW-DOGE")))     # KRW-SBD 조회
    send_message('Current SBD : '+ str(upbit.get_balance("KRW-SBD")))     # KRW-SBD 조회
    send_message('Current XLM : '+ str(upbit.get_balance("KRW-XLM")))     # KRW-XLM 조회

def reset_state():
    send_message("==========")
    send_message("State Init")
    # 초기 정보 
    now = datetime.datetime.now()                       # 현재시간을 받아옴 
    start_time = get_start_time("KRW-ETH")              #9:00
    end_time = start_time + datetime.timedelta(days=1)  #9:00 + 1일

    send_message("Start_Time : " + str(start_time))
    send_message("End_Time : " + str(end_time))

    # 코인 배팅 설정
    krw = get_balance("KRW")            # 원화 조회

    krw_eth = krw * 0.5     #이더리움
    krw_xrp = krw * 0.2     #리플
    krw_etc = krw * 0.15     #이더리움 클래식
    krw_doge = krw * 0.05     #도지코인
    krw_sbd = krw * 0.05     #스팀달러
    krw_xlm = krw * 0.05     #스텔라루멘

    send_message('eth : '+str(krw_eth))    
    send_message('xrp : '+str(krw_xrp))    
    send_message('etc : '+str(krw_etc))    
    send_message('doge: '+str(krw_doge))    
    send_message('sbd : '+str(krw_sbd))    
    send_message('xlm : '+str(krw_xlm))    

    

def send_message(text): 
    now = datetime.datetime.now()                       # 현재시간을 받아옴 
    date_time = now.strftime("%m/%d, %H:%M:%S")
    send_message_to_slack("[" + date_time +"]" + text)

def send_message_to_slack(text): 
    url = "https://hooks.slack.com/services/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"
    payload = { "text" : text }
    requests.post(url, json=payload)

# 로그인
upbit = pyupbit.Upbit(access, secret)
print("login")
send_message_to_slack("ggggg")
send_message("Auto BitCoin Trade Start!!")

show_current_state()

reset_state()

# 자동매매 시작
while True:
    try:
        now = datetime.datetime.now()                       # 현재시간을 받아옴 
        start_time = get_start_time("KRW-ETH")              #9:00
        end_time = start_time + datetime.timedelta(days=1)  #9:00 + 1일
        
        krw = get_balance("KRW")            # 원화 조회
        if krw < 5000:
            time.sleep(1)
            continue
        # 매수 로직 -  9:00 < 현재 < #8:59:50
        if start_time < now < end_time - datetime.timedelta(seconds=10):
            
            #1.ETH
            target_price_eth = get_target_price("KRW-ETH", 0.5)     #목표값 설정 
            current_price_eth = get_current_price("KRW-ETH")        # 현재 값
            if target_price_eth < current_price_eth:        # 목표값 < 현재값
                if krw_eth > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-ETH", krw_eth*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                    krw_eth = 0
                    send_message('ETH Order : '+str(krw_eth * 0.9995))
            
            #2.XRP
            target_price_xrp = get_target_price("KRW-XRP", 0.5)     #목표값 설정 
            current_price_xrp = get_current_price("KRW-XRP")        # 현재 값
            if target_price_xrp < current_price_xrp:        # 목표값 < 현재값
                if krw_xrp > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-XRP", krw_xrp*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                    send_message('XRP Order : '+str(krw_xrp * 0.9995))
                    krw_xrp = 0
                
            #3.ETC
            target_price_etc = get_target_price("KRW-ETC", 0.5)     #목표값 설정 
            current_price_etc = get_current_price("KRW-ETC")        # 현재 값
            if target_price_etc < current_price_etc:        # 목표값 < 현재값
                if krw_etc > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-ETC", krw_etc*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정        
                    send_message('ETC Order : '+str(krw_etc * 0.9995))
                    krw_etc = 0
                
            #4.DOGE
            target_price_doge = get_target_price("KRW-DOGE", 0.5)     #목표값 설정 
            current_price_doge = get_current_price("KRW-DOGE")        # 현재 값
            if target_price_doge < current_price_doge:        # 목표값 < 현재값
                if krw_doge > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-DOGE", krw_doge*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정        
                    send_message('DOGE Order : '+str(krw_doge * 0.9995))
                    krw_doge = 0

            #5.SBD
            target_price_sbd = get_target_price("KRW-SBD", 0.5)     #목표값 설정 
            current_price_sbd = get_current_price("KRW-SBD")        # 현재 값
            if target_price_sbd < current_price_sbd:        # 목표값 < 현재값
                if krw_sbd > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-SBD", krw_sbd*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정        
                    send_message('SBD Order : '+str(krw_sbd * 0.9995))
                    krw_sbd = 0

            #6.XLM
            target_price_xlm = get_target_price("KRW-XLM", 0.5)     #목표값 설정 
            current_price_xlm = get_current_price("KRW-XLM")        # 현재 값
            if target_price_xlm < current_price_xlm:        # 목표값 < 현재값
                if krw_xlm > 5000:                      # 원화가 5000보다 크면
                    upbit.buy_market_order("KRW-XLM", krw_xlm*0.9995)       #비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정        
                    send_message('XLM Order : '+str(krw_xlm * 0.9995))
                    krw_sbd = 0

    #    매수 로직 -  9:00 < 현재 < #8:59:50
        # 매도 로직 - 8:59:51 ~ 9:00:00
        elif end_time - datetime.timedelta(seconds=10) < now < end_time - datetime.timedelta(seconds=2):
            send_message("Sell Time")
            ehc = get_balance("KRW-ETH")
            if ehc > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-ETH", ehc*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료
                send_message('ETH sell : '+str(ehc * 0.9995))
            
            xrp = get_balance("KRW-XRP")
            if xrp > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-XRP", xrp*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료
                send_message('XRP sell : '+str(xrp * 0.9995))

            etc = get_balance("KRW-ETC")
            if etc > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-ETC", etc*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료
                send_message('ETC sell : '+str(etc * 0.9995))

            doge = get_balance("KRW-DOGE")
            if doge > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-DOGE", doge*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료
                send_message('DOGE sell : '+str(doge * 0.9995))

            sbd = get_balance("KRW-SBD")
            if sbd > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-SBD", sbd*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료
                send_message('SBD sell : '+str(sbd * 0.9995))

            xlm = get_balance("KRW-XLM")
            if xlm > 0.00008:           #최소 거래금액 가격 : 0.00008
                upbit.sell_market_order("KRW-XLM", xlm*0.9995)          #비트코인 매도 로직 - 수수료 0.0005 고료
                send_message('XLM sell : '+str(xlm * 0.9995))

        else:
            send_message("Reset Time")
            reset_state()
        time.sleep(1)
        
    except Exception as e:
        send_message('Exception!!!! : '+e)
        print(e)
        time.sleep(1)