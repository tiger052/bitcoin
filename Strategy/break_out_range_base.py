#########################
#    변동성 돌파 전략 기본  #
#########################
import string

from Util.notifier import *
from Api.upbit import *
from Util.time_helper import *
from Util.file_helper import *
from Util.make_up_universe import *

import sys
import os
import time
import traceback
import threading
from enum import Enum

class TradeState(Enum):
    initialize = "init"                         # 초기화 단계 : Ticer 정보 및 현재 Coin 상태를 설정 및 초기화 한다.
    ready = "ready"                             # 준비 단계 : 매수 전 데이터를 수집하는 단계 (변동성 + 하락 + 효율 )
    wait_for_start = "wait_for_start"           # 시작 대기 단계 : 준비는 완료 됬으며 Trade를 시작 하기 전 단계
    trading = "trading"                         # 트레이딩 단계 : 매수를 시도하는 단계
    complete_trade = "complete_trade"           # 트레이드 한 상태 : 매수 처리가 완료된 상태 (변동성)
    drop_check = "drop_check"                   # 하락 체크 상태 : 매수한 코인이 하락 하는지 체크 (변동성 + 하락)
    selling = "selling"                         # 매도 상태 : 매도를 시도하는 단계
    complete_sell = "complete_sell"             # 매도 된 상태 : 매도 처리가 완료된 상태
    waiting = "waiting"                         # 대기 중

class BreakOutRange(threading.Thread):
    def __init__(self):

        threading.Thread.__init__(self)
        # -- Login
        self.upbitInst = create_instance()

        # -- 트레이드 셋팅
        self.strategy_name = "break_out_range"
        self.targetCoin = ""  # 트레이드 할 Coin
        self.tradeState = TradeState.initialize  # 트레이드 상태
        self.processState = ProcessState.complete  # 처리 상태
        self.universeType = BreakOutRangeUniverse.drawdown_rank   # Universe Type 설정

        # -- 트레이딩 수치값
        self.targetPercent = 0.5  # 변동성 돌파 목표치 비율
        self.is_init_success = True
        self.tradeVolumeMin = 5000  # 최소 거래 값 - 5000원 이상
        self.tradeVolumeMax = 10000  # 최대 거래 값 - 10000원
        self.AllowCoinPrice = 5000  # 1 coin 당 최소 코인 가격
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
        self.ticker_dic = {}                                 # Tickers 전체 dic (key : code , value : 한글명 이름)
        self.trade_coin_list = []  # 거래할 코인 list (코인 최소 가격으로 걸러진 금액)
        self.used_coin_dic = {}  # 매수시 Dictionary에 저장하여 관리 (매도시 사용)
        self.buy_price = 0  # 매수 시 금액
        self.sell_price = 0  # 판매 하기 위한 금액
        self.max_price = 0  # 매수 후 최고 가격

        saveLog("{}[{}] - [{} 시작]".format("=========================\n",datetime.now(), self.strategy_name))
        send_message("{}[{}] - {} 시작".format("=========================\n",datetime.now(), self.strategy_name))
        saveLog("\n[{}] - [TradeState - initialize]".format(datetime.now()))


    # 전략 초기화 기능을 수행하는 함수
    def init_strategy(self):
        try:
            self.get_account_info()
            init_time_info()  # 당일 시간을 Reset 한다.
            saveLog(">> 초기화 완료.\n\n[{}] - [TradeState - ready]".format(datetime.now()))
            self.tradeState = TradeState.ready
        except Exception as e:
            print(traceback.format_exc())
            send_message(traceback.format_exc())

    def reset_strategy(self):
        self.processState = ProcessState.processing

        self.curCoinIdx = 0  # 현재 코인의 Index
        self.sell_price = 0  # 매수 가
        self.trade_coin_list.clear()
        self.used_coin_dic.clear()
        self.tickerlist.clear()
        self.ticker_dic.clear()
        self.get_coin_list_by_market()
        make_universe_data_bor(self.tickerlist,0.5,"universe", 5)
        self.make_trade_coin_list()     # 거래한 코인 정보를 생성한다.
        init_time_info()  # 당일 시간을 Reset 한다.

        self.processState = ProcessState.complete
        self.tradeState = TradeState.wait_for_start
        clearLog()
        send_message("{}".format(self.show_account_Info()))
        saveLog("{}".format(self.show_account_Info()))
        saveLog(">> 전략 준비 완료.\n\n[{}] - [TradeState - wait_for_start]".format(datetime.now()))

    def get_account_info(self):
        saveLog("{}".format(">>> setAccount!"))
        accountInfo = get_account()
        time.sleep(1)
        self.targetCoin = ""
        for data in accountInfo:
            print(data)
            if data['currency'] == 'BTC' or data['currency'] == 'KRW':
                continue
            coinKey = "{}-{}".format(data['unit_currency'],data['currency'])
            self.used_coin_dic[coinKey] = data['balance']
            self.targetCoin = coinKey

    def show_account_Info(self):
        accountInfo = get_account()
        totalBuy = 0
        totalCur = 0
        msg = ""
        for data in accountInfo:
            if data['currency'] == 'KRW':
                continue
            krw = float(data['balance']) * float(data['avg_buy_price'])
            coin = "{}-{}".format(data['unit_currency'],data['currency'])
            curPrice = get_current_price(coin) * float(data['balance'])
            coininfo = "[{} / {:.2f} -> {:.2f} / {:.2f}], ".format(self.ticker_dic[coin], krw, curPrice, curPrice - krw)

            totalBuy = totalBuy + krw
            totalCur = totalCur + curPrice
            msg = msg + coininfo
            time.sleep(0.2)
        msg = msg + "[전체 / {:.2f} -> {:.2f} / {:.2f}]".format(totalBuy, totalCur, totalCur - totalBuy)
        return msg

    def get_coin_list_by_market(self):
        print(">>> Check Coin Info Start!")
        self.tickerlist = get_ticker("KRW", False, False, True)  # ticker 리스터 획득
        print(">> ticker list - {}, {}".format(len(self.tickerlist), self.tickerlist))

    def make_trade_coin_list(self):
        # 전체 Coin 정보 저장
        for ticker in self.tickerlist:
            self.ticker_dic[ticker['market']] = ticker['korean_name']  # KRW-MTL = '메탈'
            curprice = get_current_price(ticker['market'])
            time.sleep(0.2)
            balance = get_balance(self.upbitInst, ticker['market'])
            if balance > 0:
                if curprice * balance > 5000:       # 팔수 있는 상태 일경우 만 등록 (5000원 미만은 거래 불가)
                    self.used_coin_dic[ticker['market']] = balance

        # Trade 할 Coin List
        if self.universeType == BreakOutRangeUniverse.limit_price:
            self.trade_coin_list = get_universe_bor_limit_price(5,5000)
        elif self.universeType == BreakOutRangeUniverse.drawdown_rank:
            self.trade_coin_list = get_universe_bor_drawdown_rank(5, 5)

        if self.targetCoin is "":
            self.targetCoin = self.trade_coin_list[0]

        print(">> Universe Type - {}".format(self.universeType))
        print(">> used coin dic - size : {}, dic : {} ".format(len(self.used_coin_dic), self.used_coin_dic))
        print(">> real coin list - size : {}, list : {}".format(len(self.trade_coin_list), self.trade_coin_list))
        print(">> current Target Coin - {} : {}".format(self.targetCoin, self.ticker_dic[self.targetCoin]))
        print(">>> Complete Check Coin Info")

        send_message("[{}] 금일 코인 정보 - [{}] , universe type - {}, coin list -{}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.tradeState, self.universeType, self.trade_coin_list))

    def next_trade_coin(self):
        self.curCoinIdx = self.curCoinIdx + 1
        if self.curCoinIdx > len(self.trade_coin_list) - 1:
            self.curCoinIdx = 0
        self.targetCoin = self.trade_coin_list[self.curCoinIdx]

    def report_transaction_info(self, text):
        # 3.4 Log 저장 로직
        now = datetime.now()
        if check_one_minute_time():  # 분당 저장
            saveLog(">> [{}] 분당 보고 - [{}] , {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.tradeState, text))

        # 하루 마감시 마지막 Log 전송
        if check_last_time():
            send_message("[{}] 하루 마감 보고 - [{}] , {}".format(now.strftime('%Y-%m-%d %H:%M:%S'),self.tradeState, text))
            saveLog("{}".format(self.show_account_Info()))

        # 3.5 정시 정기 보고
        if check_on_time():
            send_message("[{}] 정시 정기 보고 - [{}],{}\n{}".format(now.strftime('%Y-%m-%d %H:%M:%S'),self.tradeState, self.show_account_Info(), text))
            saveLog("{}".format(self.show_account_Info()))

    def run(self):
        """실질적 수행 역할을 하는 함수"""
        while True:
            try:
                time.sleep(1)
                if self.processState == ProcessState.processing:
                    continue

                if self.tradeState == TradeState.initialize:  # 1. 초기화
                    if check_adjacent_transaction_closed():
                        if self.targetCoin == "":
                            saveLog(">>초기화 준비 시간. 타겟 코인 없음 - [{}]".format(datetime.now()))
                        else:
                            saveLog(">>초기화 준비 시간. 타겟 코인 있음 - [{}]".format(datetime.now()))
                    else:       # 8:46~9:00 는 대기
                        saveLog(">>초기화 시작 시간. - [{}]".format(datetime.now()))
                        self.init_strategy()
                elif self.tradeState == TradeState.ready:    # 2. 설정 초기화
                    if check_transaction_open():
                        self.reset_strategy()
                    else:       # 8:46~9:00 는 대기
                        target_price = get_target_price(self.targetCoin, self.targetPercent)  # 목표값 설정
                        current_price = get_current_price(self.targetCoin)  # 현재 값
                        krw = get_balance(self.upbitInst, "KRW")  # 원화 조회
                        unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인
                        self.report_transaction_info("KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(krw,self.ticker_dic[self.targetCoin],unit,target_price,current_price))

                elif self.tradeState == TradeState.wait_for_start:      #3. 시작 전 대기 상태
                    if check_transaction_open():
                        self.tradeState = TradeState.trading
                        saveLog(">> 트레이딩 시작.\n\n[{}] - [TradeState - trading]".format(datetime.now()))
                    else:       # 8:46~9:00 는 대기
                        target_price = get_target_price(self.targetCoin, self.targetPercent)  # 목표값 설정
                        current_price = get_current_price(self.targetCoin)  # 현재 값
                        krw = get_balance(self.upbitInst, "KRW")  # 원화 조회
                        unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인
                        self.report_transaction_info("KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(krw,self.ticker_dic[self.targetCoin],unit,target_price,current_price))

                elif self.tradeState == TradeState.trading:  # 4. 트레이딩
                    target_price = get_target_price(self.targetCoin, self.targetPercent)  # 목표값 설정
                    current_price = get_current_price(self.targetCoin)  # 현재 값
                    krw = get_balance(self.upbitInst, "KRW")  # 원화 조회
                    unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인
                    # trading max 값 설정
                    target_krw = 0
                    if krw > self.tradeVolumeMax:
                        target_krw = self.tradeVolumeMax
                    else:
                        target_krw = krw

                    # 3.2 매수 로직 -  당일 9:00 < 현재 < # 명일 8:59:45
                    if check_transaction_open():
                        if target_krw > self.tradeVolumeMin:  # 원화가 5000보다 크면
                            if target_price < current_price:  # 목표값 < 현재값 -> 변동성 돌파 조건
                                if self.isAutoChangeCoin == True:
                                    if current_price > self.AllowCoinPrice:  # 허용 수치 보다 크다면 -> 비싼 가격의 Coin은 제외 하자
                                        self.next_trade_coin()
                                        self.report_transaction_info("STATE : {},  KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(self.tradeState.value, krw, self.ticker_dic[self.targetCoin], unit, target_price, current_price))
                                        time.sleep(1)
                                        continue
                                # 구매 로직 - 시장가
                                self.upbitInst.buy_market_order(self.targetCoin,target_krw * self.feePercent)  # 비트코인 매수 로직 - 수수료 0.0005를 고려해서 0.9995로 지정
                                self.used_coin_dic[self.targetCoin] = current_price  # 매수 dic에 저장
                                saveLog(">>[{}] 매수 - KRW :{}, Coin Name :{}, Unit :{}, Target Price :{}, Current Price :{}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),krw,self.ticker_dic[self.targetCoin], unit, target_price, current_price))
                                send_message("[{}] 매수!!!\n{} - {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), self.ticker_dic[self.targetCoin], 5000 * self.feePercent))

                                self.tradeState = TradeState.complete_trade
                                saveLog(">>Buy Complete\n\n[{}] - [TradeState - complete_trade]".format(datetime.now()))
                            else:
                                if self.isAutoChangeCoin == True:
                                    self.next_trade_coin()
                        else:  # 원화가 없으면 매수 모드에서는 아무것도 처리하지 않는다.
                            self.tradeState = TradeState.complete_trade
                            saveLog(">>원화 부족 : {}\n\n[{}] - [TradeState - complete_trade]".format(krw,datetime.now()))

                        self.report_transaction_info("STATE : {},  KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(self.tradeState.value, krw, self.ticker_dic[self.targetCoin], unit, target_price, current_price))
                    else:   # 8:46~9:00 는 대기
                        self.tradeState = TradeState.selling
                        saveLog(">>거래 시간 종료\n\n[{}] - [TradeState - complete_trade]".format(datetime.now()))

                elif self.tradeState == TradeState.complete_trade:
                    # 구매 여부 확인 로직
                    unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인
                    if unit > 0:
                        saveLog(">>해당 코인 보유 중 . coin :{} , unit : {}\n\n[{}] - [TradeState - waiting]".format(self.ticker_dic[self.targetCoin], unit, datetime.now()))

                    self.tradeState = TradeState.waiting
                    saveLog(">>전략 특성상 트래이드 대기 처리\n\n[{}] - [TradeState - waiting]".format(datetime.now()))

                elif self.tradeState == TradeState.waiting:
                    target_price = get_target_price(self.targetCoin, self.targetPercent)  # 목표값 설정
                    current_price = get_current_price(self.targetCoin)  # 현재 값
                    krw = get_balance(self.upbitInst, "KRW")  # 원화 조회
                    unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인

                    if check_transaction_open():
                        self.report_transaction_info("KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(krw, self.ticker_dic[self.targetCoin], unit, target_price, current_price))
                    else:   # 8:46~9:00 는 대기
                        self.tradeState = TradeState.selling
                        saveLog(">>거래 시간 종료\n\n[{}] - [TradeState - selling]".format(datetime.now()))

                elif self.tradeState == TradeState.selling:
                    # 3.3 매도 로직 - 명일 8:59:46 ~ 9:00:00
                    target_price = get_target_price(self.targetCoin, self.targetPercent)  # 목표값 설정
                    current_price = get_current_price(self.targetCoin)  # 현재 값
                    krw = get_balance(self.upbitInst, "KRW")  # 원화 조회
                    unit = get_balance(self.upbitInst, self.targetCoin)  # 보유 코인

                    if check_transaction_open():    # 9:00~8:45 는 대기
                        self.report_transaction_info("KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(krw, self.ticker_dic[self.targetCoin], unit, target_price, current_price))
                    else:   # 8:46~9:00 시 매도
                        if len(self.used_coin_dic) > 0:
                            for coin in self.used_coin_dic:
                                current_price = get_current_price(coin)  # 현재 값
                                unit = get_balance(self.upbitInst, coin)  # 보유 코인
                                if current_price * unit > 5000:
                                    self.upbitInst.sell_market_order(coin, unit)  # 비트코인 매도 로직 - 수수료 0.0005 고료
                                    self.used_coin_dic.pop(coin)
                                    saveLog("[{}] 매도 - KRW : {}, Coin Name :{}, Unit : {}, Target Price : {}, Current Price : {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),krw, self.ticker_dic[self.targetCoin], unit, target_price, current_price))
                                    send_message("[{}] 매도!!!\n{} - {}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'),self.ticker_dic[self.targetCoin], unit))
                                    break;
                        else:
                            self.tradeState = TradeState.complete_sell
                            saveLog(">>거래 완료. 남은 코인 없음\n\n[{}] - [TradeState - complete_sell]".format(datetime.now()))
                            saveLog("[{}]  매도 완료 - KRW : {}, Coin Name :{}, Unit :{}, Target Price :{}, Current Price :{}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), krw, self.ticker_dic[self.targetCoin], unit, target_price, current_price))

                        self.report_transaction_info(
                            "STATE : {},  KRW : {}, Coin Name : {}, Unit : {}, Target Price : {}, Current Price : {}".format(
                                self.tradeState.value, krw, self.ticker_dic[self.targetCoin], unit, target_price, current_price))

                elif self.tradeState == TradeState.complete_sell:
                    if check_transaction_open():    # 9:00~8:45 는 대기
                        saveLog(">>거래 가능 시간\n\n[{}] - [TradeState - ready]".format(datetime.now()))
                    else:
                        saveLog(">>거래 종료 시간\n\n[{}] - [TradeState - initialize]".format(datetime.now()))
                        self.tradeState = TradeState.initialize

            except Exception as e:
                print(traceback.format_exc())
                send_message(traceback.format_exc())
                pass