#################
# 변동성 돌파 전략 #
##################
from Util.notifier import *
from Api.upbit import *
from Util.time_helper import *
from Util.file_helper import *

import sys
import os
import time
import traceback
import threading
from enum import Enum

class TradeState(Enum):
    initialize = "init"                         # 초기화 단계 : Ticer 정보 및 현재 Coin 상태를 설정 및 초기화 한다.
    ready = "ready"                             # 준비 단계 : 매수 전 데이터를 수집하는 단계 (변동성 + 하락 + 효율 )
    trading = "trading"                         # 트레이딩 단계 : 매수를 시도하는 단계
    complete_trade = "complete_trade"           # 트레이드 한 상태 : 매수 처리가 완료된 상태 (변동성)
    drop_check = "drop_check"                   # 하락 체크 상태 : 매수한 코인이 하락 하는지 체크 (변동성 + 하락)
    selling = "selling"                         # 매도 상태 : 매도를 시도하는 단계
    complete_sell = "complete_sell"             # 매도 된 상태 : 매도 처리가 완료된 상태
    waiting = "waiting"                         # 대기 중

class BreakOutRange(threading.Thread):
    def __init__(self):

        threading.Thread.__init__(self)
        print("Break Rimoger")
        self.strategy_name = "break_out_range"
        self.upbitInst = create_instance()

        # -- 트레이드 셋팅
        self.targetCoin = "KRW-XRP"  # 트레이드 할 Coin
        self.tradeState = TradeState.initialize  # 트레이드 상태
        self.processState = ProcessState.complete  # 처리 상태

        # -- 트레이딩 수치값
        self.targetPercent = 0.5  # 변동성 돌파 목표치 비율
        self.is_init_success = True
        self.tradeVolumeMin = 5000  # 최소 거래 값 - 5000원 이상
        self.AllowCoinPrice = 5000  # 최소 코인 가격
        self.feePercent = 0.9995  # 수수료 퍼센트
        self.curCoinIdx = 0  # 현재 코인의 Index

        # -- 시스템설정
        self.isAutoChangeCoin = True  # 자동으로 Coin 변경


        # 유니버스 정보를 담을 딕셔너리
        self.universe = {}

        # 계좌 예수금
        self.deposit = 0

        # 초기화 함수 성공 여부 확인 변수
        self.is_init_success = False

        self.tickerlist = []                                 # Tickers 전체 list
        self.coinlist = []  # 거래할 코인 list (코인 최소 가격으로 걸러진 금액)
        self.usedCoindic = {}  # 매수시 Dictionary에 저장하여 관리 (매도시 사용)
        self.buy_price = 0  # 매수 시 금액
        self.sell_price = 0  # 판매 하기 위한 금액
        self.max_price = 0  # 매수 후 최고 가격
        self.init_strategy()

    def init_strategy(self):
        """전략 초기화 기능을 수행하는 함수"""

        try:
            print("init_strategy")

            ''''# 유니버스 조회, 없으면 생성
            self.check_and_get_universe()

            # 가격 정보를 조회, 필요하면 생성
            self.check_and_get_price_data()

            # Kiwoom > 주문정보 확인
            self.kiwoom.get_order()

            # Kiwoom > 잔고 확인
            self.kiwoom.get_balance()

            # Kiwoom > 예수금 확인
            self.deposit = self.kiwoom.get_deposit()

            # 유니버스 실시간 체결정보 등록
            self.set_universe_real_time()
            '''
            saveLog("[TradeState - ready]")
            self.tradeState = TradeState.ready
        except Exception as e:
            print(traceback.format_exc())
            # LINE 메시지를 보내는 부분
            #send_message(traceback.format_exc(), RSI_STRATEGY_MESSAGE_TOKEN)

    def reset_strategy(self):
        self.processState = ProcessState.processing

        self.curCoinIdx = 0  # 현재 코인의 Index
        self.sell_price = 0  # 매수 가
        self.tickerlist.clear()
        self.coinlist.clear()
        self.usedCoindic.clear()

        self.checkCoinInfo()

        self.processState = ProcessState.complete
        self.tradeState = TradeState.trading
        saveLog("[TradeState - Trading]")

    def checkCoinInfo(self):
        print("====Check Coin Info Start!====")
        self.tickerlist = list(get_ticker())  # ticker 리스터 획득
        print(">> ticker list - {}, {}".format(len(self.tickerlist), self.tickerlist))

        for ticker in self.tickerlist:
            curprice = get_current_price(ticker)
            time.sleep(0.2)
            balance = get_balance(self.upbitInst, ticker)
            if balance > 0:
                if curprice * balance > 5000:
                    self.usedCoindic[ticker] = balance
                    self.targetCoin = ticker
            if 1 < curprice < 5000:  # 소수점 이하 coin 은 배제한다
                self.coinlist.append(ticker)
        print(">> used coin dic - size : {}, dic : {} ".format(len(self.usedCoindic), self.usedCoindic))
        print(">> real coin list - size : {}, list : {}".format(len(self.coinlist), self.coinlist))
        print(">> current Target Coin - {}".format(self.targetCoin))
        print("====Complete Check Coin Info====")

    def next_coin(self):
        self.curCoinIdx = self.curCoinIdx + 1
        if self.curCoinIdx > len(self.coinlist) - 1:
            self.curCoinIdx = 0
        self.targetCoin = self.coinlist[self.curCoinIdx]

    def report_transaction_info(self,text):
        # 3.4 Log 저장 로직
        now = datetime.now()
        if check_one_minute_time():  # 분당 저장
            saveLog(">> [{}] 분당 보고 - {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), text))

        # 하루 마감시 마지막 Log 전송
        if check_last_time():
            send_message("[{}] 하루 마감 보고 - {}".format(now.strftime('%Y-%m-%d %H:%M:%S'),text))

        # 3.5 정시 정기 보고
        if check_on_time():
            send_message("[{}] 정시 정기 보고 - {}".format(now.strftime('%Y-%m-%d %H:%M:%S'), text))

    def run(self):
        """실질적 수행 역할을 하는 함수"""
        while True:
            try:
                time.sleep(1)
                if self.processState == ProcessState.processing:
                    continue

                if self.tradeState == TradeState.initialize:  # 1. 초기화
                    continue

                elif self.tradeState == TradeState.ready:    # 2. 설정 초기화
                    self.reset_strategy()

                elif self.tradeState == TradeState.trading:  # 3. 트레이딩
                    target_price = get_target_price(self.targetCoin, self.targetPercent)  # 목표값 설정
                    current_price = get_current_price(self.targetCoin)  # 현재 값
                    krw = get_balance(self.upbitInst, "KRW")  # 원화 조회
                    unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인

                    # 3.2 매수 로직 -  당일 9:00 < 현재 < # 명일 8:59:45
                    if check_transaction_open():
                        if krw > self.tradeVolumeMin:  # 원화가 5000보다 크면
                            if target_price < current_price:  # 목표값 < 현재값
                                if self.isAutoChangeCoin == True:
                                    if current_price > self.AllowCoinPrice:  # 허용 수치 보다 크다면
                                        self.next_coin()
                                        self.report_transaction_info("STATE : {},  KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(self.tradeState.value, krw, self.targetCoin, unit, target_price, current_price))
                                        time.sleep(1)
                                        continue

                                self.upbitInst.buy_market_order(self.targetCoin,
                                                           krw * self.feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                                self.usedCoindic[self.targetCoin] = current_price  # 매수 dic에 저장
                                saveLog(
                                    "[" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "] 매수 - KRW : " + str(
                                        krw) + ", Coin Name :" + str(
                                        self.targetCoin) + ", Unit : " + str(
                                        unit) + ", Target Price : " + str(
                                        target_price) + ", Current Price : " + str(current_price))
                                send_message("[" + datetime.now().strftime(
                                                                     '%Y-%m-%d %H:%M:%S') + "] 매수!!!\n" + str(
                                                                     self.targetCoin) + " - " + str(
                                                                     5000 * self.feePercent))

                                self.tradeState = TradeState.complete_trade
                                saveLog("[TradeState - complete_trade]")
                            else:
                                if self.isAutoChangeCoin == True:
                                    self.next_coin()
                        else:  # 원화가 없으면 매수 모드에서는 아무것도 처리하지 않는다.
                            self.tradeState = TradeState.complete_trade
                            saveLog("[TradeState - complete_trade]")

                        self.report_transaction_info(
                            "STATE : {},  KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(
                                self.tradeState.value, krw, self.targetCoin, unit, target_price, current_price))
                    else:
                        self.tradeState = TradeState.selling
                        saveLog("[TradeState - complete_trade]")

                elif self.tradeState == TradeState.complete_trade:
                    # 구매여부 확인 로직
                    unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인
                    if unit > 0:
                        self.tradeState = TradeState.waiting
                        saveLog("[TradeState - waiting] " + str(self.targetCoin) + " : " + str(unit))

                    if check_transaction_open():
                        pass
                    else:
                        self.tradeState = TradeState.selling
                        saveLog("[TradeState - selling]")

                elif self.tradeState == TradeState.waiting:
                    if check_transaction_open():
                        pass
                    else:
                        self.tradeState = TradeState.selling
                        saveLog("[TradeState - selling]")

                elif self.tradeState == TradeState.selling:
                    # 3.3 매도 로직 - 명일 8:59:46 ~ 9:00:00
                    target_price = get_target_price(self.targetCoin, self.targetPercent)  # 목표값 설정
                    current_price = get_current_price(self.targetCoin)  # 현재 값
                    krw = get_balance(self.upbitInst, "KRW")  # 원화 조회
                    unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인

                    if check_transaction_open():
                        pass
                    else:
                        if len(self.usedCoindic) > 0:
                            for coin in self.usedCoindic:
                                current_price = get_current_price(coin)  # 현재 값
                                unit = get_balance(self.upbitInst, coin)  # 보유 코인
                                if current_price * unit > 5000:
                                    self.upbitInst.sell_market_order(coin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                                    self.usedCoindic.pop(coin)
                                    saveLog(
                                        "[" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "] 매도 - KRW : " + str(
                                            krw) + ", Coin Name :" + str(
                                            self.targetCoin) + ", Unit : " + str(
                                            unit) + ", Target Price : " + str(
                                            target_price) + ", Current Price : " + str(current_price))
                                    send_message("[" + datetime.now().strftime(
                                                                         '%Y-%m-%d %H:%M:%S') + "] 매도!!!\n" + str(
                                                                         self.targetCoin) + " - " + str(unit))
                        else:
                            self.tradeState = TradeState.complete_sell
                            saveLog("[TradeState - complete_sell]")
                            saveLog(
                                "[" + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "] 매도 완료 - KRW : " + str(
                                    krw) + ", Coin Name :" + str(
                                    self.targetCoin) + ", Unit : " + str(unit) + ", Target Price : " + str(
                                    target_price) + ", Current Price : " + str(current_price))

                        self.report_transaction_info(
                            "STATE : {},  KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(
                                self.tradeState.value, krw, self.targetCoin, unit, target_price, current_price))

                        if check_transaction_open() == True:
                            self.tradeState = TradeState.ready
                            saveLog("[TradeState - ready]")

                elif self.tradeState == TradeState.complete_sell:
                    if check_transaction_open() == True:
                        self.tradeState = TradeState.ready
                        saveLog("[TradeState - ready]")

            except Exception as e:
                print(traceback.format_exc())
                # LINE 메시지를 보내는 부분
                # send_message(traceback.format_exc(), RSI_STRATEGY_MESSAGE_TOKEN)
                pass