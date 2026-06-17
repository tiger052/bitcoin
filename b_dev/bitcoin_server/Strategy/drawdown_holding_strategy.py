##################################################
# 낙폭 과대 알트코인 반등 매수 및 익절 보존 전략 #
##################################################

import json
import os
import time
import traceback
import threading
from datetime import datetime

import pyupbit
from Util.const import *
from Util.notifier import *
from Api.upbit import *
from Util.time_helper import *
from Util.file_helper import *
from Util.make_up_universe import *

class DrawdownHoldingStrategy(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.strategy_name = "drawdown_holding_strategy"
        
        # API 및 파일 설정
        self.upbitInst = create_instance()
        self.config_path = "strategy_setting.json"
        
        # 동적 설정 매개변수 초기값
        self.buy_strategy_type = BuyStrategyType.MA5_CROSSOVER
        self.sell_strategy_type = SellStrategyType.TRAILING_STOP_NO_LOSS
        self.portfolio_ratio = 0.1
        self.max_coin_count = 10
        self.trailing_stop_ratio = 0.02
        self.fixed_stop_loss_ratio = -0.03
        self.fee_buffer = 0.0015
        
        # 설정 로드
        self.load_settings()
        
        # 매매 상태 관리
        self.universe = []
        self.held_coins_max_price = {}  # {ticker: max_price_since_buy}
        self.last_universe_update_date = ""
        
        saveLog(f"\n=========================\n[{datetime.now()}] - [{self.strategy_name} 시작]")
        send_message(f"[{datetime.now()}] - {self.strategy_name} 시작\n초기 설정: 매수-{self.buy_strategy_type.value}, 매도-{self.sell_strategy_type.value}")

    def load_settings(self):
        """strategy_setting.json 설정 파일을 동적으로 파싱하여 변수에 반영"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Enum 변환 및 파라미터 업데이트
                self.buy_strategy_type = BuyStrategyType(config.get("buy_strategy", "MA5_CROSSOVER"))
                self.sell_strategy_type = SellStrategyType(config.get("sell_strategy", "TRAILING_STOP_NO_LOSS"))
                self.portfolio_ratio = float(config.get("portfolio_ratio", 0.1))
                self.max_coin_count = int(config.get("max_coin_count", 10))
                self.trailing_stop_ratio = float(config.get("trailing_stop_ratio", 0.02))
                self.fixed_stop_loss_ratio = float(config.get("fixed_stop_loss_ratio", -0.03))
                self.fee_buffer = float(config.get("fee_buffer", 0.0015))
            else:
                # 기본값 설정 파일 자동 생성
                default_config = {
                    "buy_strategy": "MA5_CROSSOVER",
                    "sell_strategy": "TRAILING_STOP_NO_LOSS",
                    "portfolio_ratio": 0.1,
                    "max_coin_count": 10,
                    "trailing_stop_ratio": 0.02,
                    "fixed_stop_loss_ratio": -0.03,
                    "fee_buffer": 0.0015
                }
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2)
        except Exception as e:
            saveLog(f">> [설정 로드 에러] {e}")

    def update_universe_daily(self):
        """매일 아침 9시 이후 거래대금 상위 30개 중 낙폭 과대 10개 코인 Universe 갱신"""
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        
        # 9시가 지났고, 오늘 날짜로 갱신된 적이 없거나 비어있는 경우
        if (now.hour >= 9 and self.last_universe_update_date != today_str) or not self.universe:
            saveLog(f">> [{now}] Universe 갱신 시작...")
            send_message(f"[{now}] Universe 코인 분석 및 갱신 시작...")
            
            # make_up_universe의 거래대금 낙폭 과대 로직 호출
            new_universe = get_high_volume_drawdown_universe(top_n=30, select_count=10)
            if new_universe:
                self.universe = new_universe
                self.last_universe_update_date = today_str
                saveLog(f">> [{now}] Universe 갱신 완료: {self.universe}")
                send_message(f"오늘의 매수 감시 대상 코인 리스트:\n{', '.join(self.universe)}")
            else:
                saveLog(f">> [{now}] Universe 갱신 실패 (기존 리스트 유지): {self.universe}")

    def check_buy_condition(self, ticker):
        """모듈화된 매수 진입 시점 판정"""
        try:
            current_price = get_current_price(ticker)
            time.sleep(0.1)
            
            # A. 1시간 봉 기준 MA5선 돌파 (디폴트)
            if self.buy_strategy_type == BuyStrategyType.MA5_CROSSOVER:
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=6)
                if df is not None and len(df) >= 5:
                    ma5 = df['close'].rolling(5).mean().iloc[-1]
                    if current_price > ma5:
                        return True
            
            # B. 당일 시가 대비 +1.5% 상승 돌파
            elif self.buy_strategy_type == BuyStrategyType.OPEN_BREAKOUT:
                df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
                if df is not None and not df.empty:
                    open_price = df.iloc[0]['open']
                    if current_price >= open_price * 1.015:
                        return True
            
            # C. 15분 봉 기준 3연속 양봉
            elif self.buy_strategy_type == BuyStrategyType.CANDLE_3_GREEN:
                df = pyupbit.get_ohlcv(ticker, interval="minute15", count=4)
                if df is not None and len(df) >= 4:
                    c1 = df.iloc[-4]['close'] > df.iloc[-4]['open']
                    c2 = df.iloc[-3]['close'] > df.iloc[-3]['open']
                    c3 = df.iloc[-2]['close'] > df.iloc[-2]['open']
                    c_now = current_price > df.iloc[-1]['open']
                    if c1 and c2 and c3 and c_now:
                        return True
                        
        except Exception as e:
            saveLog(f">> [매수 판정 에러] {ticker}: {e}")
        return False

    def check_sell_condition(self, ticker, avg_buy_price, current_price):
        """모듈화된 매도 시점 판정"""
        try:
            # 원금 + 수수료 기준 손익분기점 계산
            breakeven_price = avg_buy_price * (1.0 + self.fee_buffer)
            
            # 1. 고정 손절 (FIXED_STOP_LOSS) 전략 - 수수료/손익분기 무시하고 원금 대비 강제 손절 비율 도달 시 매도
            if self.sell_strategy_type == SellStrategyType.FIXED_STOP_LOSS:
                stop_loss_price = avg_buy_price * (1.0 + self.fixed_stop_loss_ratio)
                if current_price <= stop_loss_price:
                    saveLog(f">> [고정 손절 트리거] {ticker} 현재가: {current_price} <= 손절가: {stop_loss_price}")
                    return True

            # 손익분기점 미만이면 매도를 원천 차단 (존버 정책)
            if current_price < breakeven_price:
                # 손익분기점 아래에서는 절대 팔지 않음
                return False

            # --- 이 하 조건은 손익분기점(이익 구간)에 도달한 상황 ---
            
            # 최고가 트래킹 갱신
            if ticker not in self.held_coins_max_price:
                self.held_coins_max_price[ticker] = current_price
            else:
                self.held_coins_max_price[ticker] = max(current_price, self.held_coins_max_price[ticker])
            
            max_price = self.held_coins_max_price[ticker]

            # 2. 트레일링 익절 보존 (TRAILING_STOP_NO_LOSS) - 최고점 대비 특정 비율 하락 시 매도
            if self.sell_strategy_type == SellStrategyType.TRAILING_STOP_NO_LOSS:
                trailing_trigger_price = max_price * (1.0 - self.trailing_stop_ratio)
                
                # 최고점 대비 하락하였고, 그 하락한 가격도 여전히 손익분기점 이상인 안전 영역일 때만 매도
                if current_price <= trailing_trigger_price and current_price >= breakeven_price:
                    saveLog(f">> [트레일링 스탑 트리거] {ticker} 현재가: {current_price} <= 트리거가: {trailing_trigger_price} (최고가: {max_price})")
                    return True
            
            # 3. 순수 존버 (HODL_NO_LOSS) - 자동 매도를 일체 하지 않고 사용자가 직접 처리하거나 고수익 목표 대기
            elif self.sell_strategy_type == SellStrategyType.HODL_NO_LOSS:
                # 이익 구간이라도 자동 매도를 수행하지 않음 (존버)
                return False
                
        except Exception as e:
            saveLog(f">> [매도 판정 에러] {ticker}: {e}")
        return False

    def get_account_balances(self):
        """계좌 정보 조회 및 보유 자산 계산"""
        balances = {}
        krw = 0.0
        total_assets = 0.0
        
        try:
            account_info = get_account()
            time.sleep(0.2)
            
            if not isinstance(account_info, list):
                saveLog(f">> [계좌 조회 오류] Upbit 응답 에러: {account_info}")
                return krw, total_assets, balances
                
            for asset in account_info:
                currency = asset.get('currency')
                unit_currency = asset.get('unit_currency')
                balance = float(asset.get('balance', 0))
                avg_buy_price = float(asset.get('avg_buy_price', 0))
                
                if currency == 'KRW':
                    krw = balance
                    total_assets += krw
                else:
                    ticker = f"{unit_currency}-{currency}"
                    # 보유 코인의 현재 평가 금액 계산
                    cur_price = get_current_price(ticker)
                    time.sleep(0.1)
                    val = balance * cur_price
                    total_assets += val
                    balances[ticker] = {
                        'balance': balance,
                        'avg_buy_price': avg_buy_price,
                        'current_price': cur_price,
                        'value': val
                    }
        except Exception as e:
            saveLog(f">> [계좌 조회 에러] {e}")
            
        return krw, total_assets, balances

    def run(self):
        saveLog(">> 트레이딩 스레드 루프 진입.")
        
        # 초기 시간 정보 세팅
        init_time_info()
        
        while True:
            try:
                # 1. 실시간 동적 설정 로드
                self.load_settings()
                
                # 2. 일일 감시 대상 코인 Universe 갱신 (오전 9시 기준)
                self.update_universe_daily()
                
                # 3. 계좌 현황 및 자산 파악
                krw, total_assets, balances = self.get_account_balances()
                held_count = len(balances)
                
                # 매수 예산 계산 (총 자산의 portfolio_ratio 만큼 배분)
                buy_budget_per_coin = total_assets * self.portfolio_ratio
                
                # 4. 보유 중인 코인들 매도 감시
                for ticker, info in list(balances.items()):
                    avg_buy_price = info['avg_buy_price']
                    current_price = info['current_price']
                    
                    if self.check_sell_condition(ticker, avg_buy_price, current_price):
                        # 매도 주문 집행
                        saveLog(f">> [매도 집행] {ticker} 전량 매도 진행 (수량: {info['balance']}, 현재가: {current_price})")
                        self.upbitInst.sell_market_order(ticker, info['balance'])
                        send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 매도 완료!!!\n코인: {ticker}\n평단가: {avg_buy_price:.2f} -> 매도가: {current_price:.2f}")
                        
                        # 트래킹 데이터 삭제
                        if ticker in self.held_coins_max_price:
                            del self.held_coins_max_price[ticker]
                        
                        # 매도 처리 후 계좌 업데이트를 위해 잠시 대기 및 루프 재시작
                        time.sleep(1)
                        break

                # 5. 매수 감시 (보유 한도 미만이고 원화 잔고가 5000원 이상 있을 때만)
                if held_count < self.max_coin_count and krw >= 5000:
                    # 실제 매수할 금액 (원화 잔고와 종목당 설정 예산 중 최소값 선택)
                    actual_buy_amount = min(buy_budget_per_coin, krw)
                    
                    if actual_buy_amount >= 5000:
                        for ticker in self.universe:
                            # 이미 보유 중인 코인이면 매수 대상에서 제외
                            if ticker in balances:
                                continue
                                
                            # 매수 신호 판정
                            if self.check_buy_condition(ticker):
                                saveLog(f">> [매수 집행] {ticker} 시장가 매수 진행 (금액: {actual_buy_amount})")
                                # 수수료 버퍼를 고려하여 주문 금액 설정
                                self.upbitInst.buy_market_order(ticker, actual_buy_amount * 0.9995)
                                cur_price = get_current_price(ticker)
                                send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 매수 완료!!!\n코인: {ticker}\n매수 금액: {actual_buy_amount:.2f}원 (체결가: {cur_price:.2f})")
                                
                                # 매수한 코인의 최고가 트래킹 초기화
                                self.held_coins_max_price[ticker] = cur_price
                                
                                # 매수 처리 후 밸런스가 변하므로 즉시 루프 재시작
                                time.sleep(1)
                                break

                # 매 루프 후 출력할 모니터링 로그 (1분 단위 저장)
                if check_one_minute_time():
                    status_text = f"자산 총액: {total_assets:.2f}원 | 원화 잔고: {krw:.2f}원 | 보유 종목 수: {held_count}/{self.max_coin_count}\n"
                    status_text += f"현재 설정: 매수-{self.buy_strategy_type.value}, 매도-{self.sell_strategy_type.value}"
                    if held_count > 0:
                        status_text += "\n보유 현황:\n"
                        for t, inf in balances.items():
                            pl_ratio = ((inf['current_price'] - inf['avg_buy_price']) / inf['avg_buy_price']) * 100
                            status_text += f" - {t}: 평단 {inf['avg_buy_price']:.2f} -> 현재 {inf['current_price']:.2f} ({pl_ratio:+.2f}%)\n"
                    saveLog(f">> [실시간 상태]\n{status_text}")
                
                # 10초 대기 후 루프 반복
                time.sleep(10)
                
            except Exception as e:
                print(traceback.format_exc())
                send_message(f"[에러 알림] {self.strategy_name} 루프 예외 발생:\n{e}")
                time.sleep(10)
