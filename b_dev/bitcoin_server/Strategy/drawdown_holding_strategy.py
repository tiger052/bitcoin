##################################################
# 낙폭 과대 알트코인 반등 매수 및 익절 보존 전략 #
##################################################

import json
import os
import time
import traceback
import threading
from datetime import datetime, timedelta

import pyupbit
from Util.const import *
from Util.notifier import *
from Api.upbit import *
from Util.time_helper import *
from Util.file_helper import *
from Util.make_up_universe import *

def calculate_rsi_value(df, period=14):
    if df is None or len(df) < period + 1:
        return 50.0
    try:
        delta = df['close'].diff()
        up = delta.clip(lower=0)
        down = -delta.clip(upper=0)
        ema_up = up.ewm(com=period - 1, adjust=False).mean()
        ema_down = down.ewm(com=period - 1, adjust=False).mean()
        rs = ema_up / (ema_down + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        val = rsi.iloc[-1]
        return 50.0 if np.isnan(val) else float(val)
    except Exception:
        return 50.0

def calculate_bb_values(df, period=20, std_dev=2):
    if df is None or len(df) < period:
        current_price = df['close'].iloc[-1] if df is not None and not df.empty else 0.0
        return current_price, current_price
    try:
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        u_val = upper_band.iloc[-1]
        l_val = lower_band.iloc[-1]
        current_price = df['close'].iloc[-1]
        u_val = current_price if np.isnan(u_val) else u_val
        l_val = current_price if np.isnan(l_val) else l_val
        return float(u_val), float(l_val)
    except Exception:
        current_price = df['close'].iloc[-1] if df is not None and not df.empty else 0.0
        return current_price, current_price

import numpy as np

class DrawdownHoldingStrategy(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.strategy_name = "drawdown_holding_strategy"
        
        # API 및 파일 설정
        self.upbitInst = create_instance()
        self.config_path = "strategy_setting.json"
        self.virtual_account_path = "virtual_account.json"
        
        # 동적 설정 매개변수 초기값
        self.trade_mode = "TEST"
        self.buy_strategy_type = BuyStrategyType.MA5_CROSSOVER
        self.sell_strategy_type = SellStrategyType.TRAILING_STOP_NO_LOSS
        self.portfolio_ratio = 0.1
        self.max_coin_count = 10
        self.max_buy_amount = 10000.0
        self.trailing_stop_ratio = 0.02
        self.fixed_stop_loss_ratio = -0.03
        self.fee_buffer = 0.0015
        
        # 신규 고도화 매개변수 초기값
        self.use_circuit_breaker = False
        self.is_circuit_breaker_active = False  # 실시간 비트코인 폭락 상태 플래그
        self.rsi_period = 14
        self.rsi_buy_limit = 30.0
        self.rsi_sell_limit = 70.0
        self.bb_period = 20
        self.bb_deviation = 2.0
        self.buy_strategies = [BuyStrategyType.MA5_CROSSOVER]
        self.buy_strategy_relation = "OR"
        self.sell_strategies = [SellStrategyType.TRAILING_STOP_NO_LOSS]
        self.sell_strategy_relation = "OR"
        
        # 설정 로드
        self.load_settings()
        
        # 매매 상태 관리
        self.universe = []
        self.universe_drawdowns = {}
        self.held_coins_max_price = {}  # {ticker: max_price_since_buy}
        self.last_universe_update_date = ""
        self.last_status_time = 0
        self.universe_size = 30
        self.universe_status = {}
        
        # 티커 한글 이름 로드 및 캐싱
        self.ticker_names = {}
        try:
            tickers = pyupbit.get_tickers(fiat="KRW", is_details=True)
            self.ticker_names = {item['market']: item['korean_name'] for item in tickers}
        except Exception as e:
            saveLog(f">> [티커 이름 로드 에러] {e}")
            
        saveLog(f"\n=========================\n[{datetime.now()}] - [{self.strategy_name} 시작]")
        send_message(f"[{datetime.now()}] - {self.strategy_name} 시작\n초기 설정: 모드-{self.trade_mode}, 매수-{self.buy_strategy_type.value}, 매도-{self.sell_strategy_type.value}")

    def load_settings(self):
        """strategy_setting.json 설정 파일을 동적으로 파싱하여 변수에 반영"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # Enum 변환 및 파라미터 업데이트
                self.trade_mode = config.get("trade_mode", "TEST")
                self.portfolio_ratio = float(config.get("portfolio_ratio", 0.1))
                self.max_coin_count = int(config.get("max_coin_count", 10))
                self.max_buy_amount = float(config.get("max_buy_amount", 10000.0))
                self.trailing_stop_ratio = float(config.get("trailing_stop_ratio", 0.02))
                self.fixed_stop_loss_ratio = float(config.get("fixed_stop_loss_ratio", -0.03))
                self.fee_buffer = float(config.get("fee_buffer", 0.0015))
                self.universe_size = int(config.get("universe_size", 30))
                
                # 신규 설정 항목 로드
                self.use_circuit_breaker = bool(config.get("use_circuit_breaker", False))
                self.rsi_period = int(config.get("rsi_period", 14))
                self.rsi_buy_limit = float(config.get("rsi_buy_limit", 30.0))
                self.rsi_sell_limit = float(config.get("rsi_sell_limit", 70.0))
                self.bb_period = int(config.get("bb_period", 20))
                self.bb_deviation = float(config.get("bb_deviation", 2.0))
                
                # 다중 매수 전략 파싱 & 하위 호환성 지원
                buy_str_list = config.get("buy_strategies", [])
                if not buy_str_list:
                    old_buy = config.get("buy_strategy", "MA5_CROSSOVER")
                    buy_str_list = [old_buy] if old_buy else ["MA5_CROSSOVER"]
                
                self.buy_strategies = []
                for s in buy_str_list:
                    try:
                        self.buy_strategies.append(BuyStrategyType(s))
                    except ValueError:
                        pass
                if not self.buy_strategies:
                    self.buy_strategies = [BuyStrategyType.MA5_CROSSOVER]
                
                self.buy_strategy_relation = config.get("buy_strategy_relation", "OR")
                
                # 다중 매도 전략 파싱 & 하위 호환성 지원
                sell_str_list = config.get("sell_strategies", [])
                if not sell_str_list:
                    old_sell = config.get("sell_strategy", "TRAILING_STOP_NO_LOSS")
                    sell_str_list = [old_sell] if old_sell else ["TRAILING_STOP_NO_LOSS"]
                
                self.sell_strategies = []
                for s in sell_str_list:
                    try:
                        self.sell_strategies.append(SellStrategyType(s))
                    except ValueError:
                        pass
                if not self.sell_strategies:
                    self.sell_strategies = [SellStrategyType.TRAILING_STOP_NO_LOSS]
                
                self.sell_strategy_relation = config.get("sell_strategy_relation", "OR")
                
                # 구버전 호환용 대표 단일 전략 타입 fallback 유지 (첫 번째 항목 기준)
                if self.buy_strategies:
                    self.buy_strategy_type = self.buy_strategies[0]
                if self.sell_strategies:
                    self.sell_strategy_type = self.sell_strategies[0]
            else:
                # 기본값 설정 파일 자동 생성
                default_config = {
                    "trade_mode": "TEST",
                    "buy_strategy": "MA5_CROSSOVER",
                    "sell_strategy": "TRAILING_STOP_NO_LOSS",
                    "portfolio_ratio": 0.1,
                    "max_coin_count": 10,
                    "max_buy_amount": 10000,
                    "trailing_stop_ratio": 0.02,
                    "fixed_stop_loss_ratio": -0.03,
                    "fee_buffer": 0.0015,
                    "universe_size": 30,
                    "use_circuit_breaker": False,
                    "rsi_period": 14,
                    "rsi_buy_limit": 30.0,
                    "rsi_sell_limit": 70.0,
                    "bb_period": 20,
                    "bb_deviation": 2.0,
                    "buy_strategies": ["MA5_CROSSOVER"],
                    "buy_strategy_relation": "OR",
                    "sell_strategies": ["TRAILING_STOP_NO_LOSS"],
                    "sell_strategy_relation": "OR"
                }
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            saveLog(f">> [설정 로드 에러] {e}")

    def load_virtual_account(self):
        """가상 잔고 파일 로드"""
        try:
            if os.path.exists(self.virtual_account_path):
                with open(self.virtual_account_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                default_acc = {
                    "virtual_krw": 1000000.0,
                    "virtual_balances": {}
                }
                with open(self.virtual_account_path, "w", encoding="utf-8") as f:
                    json.dump(default_acc, f, indent=2)
                return default_acc
        except Exception as e:
            saveLog(f">> [가상 계좌 로드 에러] {e}")
            return {"virtual_krw": 1000000.0, "virtual_balances": {}}

    def save_virtual_account(self, data):
        """가상 잔고 파일 저장"""
        try:
            with open(self.virtual_account_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            saveLog(f">> [가상 계좌 저장 에러] {e}")

    def load_exclude_tickers(self):
        """감시 제외 대상 코인 목록 로드"""
        exclude_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exclude_tickers.json")
        if not os.path.exists(exclude_path):
            return []
        try:
            with open(exclude_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            saveLog(f">> [제외 코인 로드 에러] {e}")
            return []

    def update_universe_daily(self):
        """매일 아침 9시 이후 거래대금 상위 30개 중 낙폭 과대 10개 코인 Universe 갱신"""
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        
        # 9시가 지났고, 오늘 날짜로 갱신된 적이 없거나 비어있는 경우, 또는 설정크기와 실제 크기가 다를 때 즉시 갱신
        if (now.hour >= 9 and self.last_universe_update_date != today_str) or not self.universe or len(self.universe) != self.universe_size:
            saveLog(f">> [{now}] Universe 갱신 시작...")
            send_message(f"[{now}] Universe 코인 분석 및 갱신 시작...")
            
            # make_up_universe의 거래대금 낙폭 과대 로직 호출
            # 감시 제외 목록을 고려하여 충분히 여유있게 가져옵니다.
            candidates = get_high_volume_drawdown_universe(top_n=max(50, self.universe_size * 3), select_count=max(50, self.universe_size * 2))
            if candidates:
                exclude_list = self.load_exclude_tickers()
                new_universe = [ticker for ticker in candidates if ticker not in exclude_list]
                new_universe = new_universe[:self.universe_size]
                
                self.universe = new_universe
                self.last_universe_update_date = today_str
                # 유니버스 변경 시 실시간 상태 정보 초기화
                self.universe_status = {}
                self.universe_drawdowns = {}
                # Calculate daily drawdown once to cache it
                for ticker in self.universe:
                    try:
                        df = pyupbit.get_ohlcv(ticker, interval="day", count=20)
                        if df is not None and not df.empty:
                            high_20d = df['high'].max()
                            current_price = df.iloc[-1]['close']
                            if high_20d > 0:
                                dd = (high_20d - current_price) / high_20d * 100
                                self.universe_drawdowns[ticker] = float(dd)
                        time.sleep(0.1)
                    except Exception as e:
                        self.universe_drawdowns[ticker] = 0.0
                saveLog(f">> [{now}] Universe 갱신 완료: {self.universe}")
                send_message(f"오늘의 매수 감시 대상 코인 리스트:\n{', '.join(self.universe)}")
            else:
                saveLog(f">> [{now}] Universe 갱신 실패 (기존 리스트 유지): {self.universe}")

    def evaluate_single_buy_condition(self, ticker, strategy_type, current_price):
        """단일 매수 전략 판정 및 상태 정보 반환"""
        try:
            trigger = False
            progress_ratio = 0.0
            signal_desc = ""
            
            # A. 1시간 봉 기준 MA5선 돌파
            if strategy_type == BuyStrategyType.MA5_CROSSOVER:
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=6)
                if df is not None and len(df) >= 5:
                    ma_val = float(df['close'].rolling(5).mean().iloc[-1])
                    trigger = current_price > ma_val
                    progress_ratio = (current_price / ma_val - 1.0) * 100 if ma_val > 0 else 0.0
                    signal_desc = f"현재 {current_price:.1f} / MA5 {ma_val:.1f}"
            
            # B. 당일 시가 대비 +1.5% 상승 돌파
            elif strategy_type == BuyStrategyType.OPEN_BREAKOUT:
                df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
                if df is not None and not df.empty:
                    open_price = float(df.iloc[0]['open'])
                    target_price = open_price * 1.015
                    trigger = current_price >= target_price
                    progress_ratio = (current_price / target_price - 1.0) * 100 if target_price > 0 else 0.0
                    signal_desc = f"현재 {current_price:.1f} / 시가 {open_price:.1f} (+1.5% 목표: {target_price:.1f})"
            
            # C. 15분 봉 기준 3연속 양봉
            elif strategy_type == BuyStrategyType.CANDLE_3_GREEN:
                df = pyupbit.get_ohlcv(ticker, interval="minute15", count=4)
                if df is not None and len(df) >= 4:
                    c1 = df.iloc[-4]['close'] > df.iloc[-4]['open']
                    c2 = df.iloc[-3]['close'] > df.iloc[-3]['open']
                    c3 = df.iloc[-2]['close'] > df.iloc[-2]['open']
                    c_now = current_price > df.iloc[-1]['open']
                    trigger = c1 and c2 and c3 and c_now
                    
                    green_cnt = sum([c1, c2, c3, c_now])
                    progress_ratio = (green_cnt / 4.0) * 100
                    signal_desc = f"양봉 조건 충족: {green_cnt}/4개 완료"
    
            # D. 1시간 봉 기준 RSI 과매도 반등 (RSI <= rsi_buy_limit)
            elif strategy_type == BuyStrategyType.RSI_OVERSOLD:
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=30)
                if df is not None and len(df) >= 15:
                    rsi_val = calculate_rsi_value(df, period=self.rsi_period)
                    trigger = rsi_val <= self.rsi_buy_limit
                    progress_ratio = rsi_val
                    signal_desc = f"현재 RSI: {rsi_val:.1f} (과매도 기준: {self.rsi_buy_limit:.1f})"
    
            # E. 1시간 봉 기준 볼린저 밴드 하단 돌파 터치 반등
            elif strategy_type == BuyStrategyType.BB_LOWER_TOUCH:
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=30)
                if df is not None and len(df) >= self.bb_period:
                    upper_band, lower_band = calculate_bb_values(df, period=self.bb_period, std_dev=self.bb_deviation)
                    trigger = current_price <= lower_band
                    progress_ratio = (current_price / lower_band - 1.0) * 100 if lower_band > 0 else 0.0
                    signal_desc = f"현재 {current_price:.0f} / BB하단 {lower_band:.0f}"
                    
            return trigger, progress_ratio, signal_desc
        except Exception as e:
            saveLog(f">> [단일 매수 판정 오류] {ticker} - {strategy_type}: {e}")
            return False, 0.0, f"에러: {e}"

    def check_buy_condition(self, ticker):
        """모듈화된 매수 진입 시점 판정 및 실시간 값 기록 (다중 전략 AND/OR 결합)"""
        try:
            current_price = get_current_price(ticker)
            time.sleep(0.1)
            
            results = []
            for s in self.buy_strategies:
                res = self.evaluate_single_buy_condition(ticker, s, current_price)
                results.append((s, res[0], res[1], res[2])) # (strategy, trigger, progress_ratio, signal_desc)
                
            if not results:
                return False
                
            # AND / OR 결합 판단
            if self.buy_strategy_relation == "AND":
                final_trigger = all(r[1] for r in results)
            else:
                final_trigger = any(r[1] for r in results)
                
            # UI에 보여줄 대표값 추출 (트리거된 전략이 있으면 그것을 대표로 우선 표시, 없으면 첫 번째 기준)
            rep_ratio = results[0][2]
            for r in results:
                if r[1]:
                    rep_ratio = r[2]
                    break
                    
            rep_desc = " | ".join(f"[{r[0].value}] {r[3]}" for r in results)
            
            # 상태 기록 업데이트
            self.universe_status[ticker] = {
                "current_price": float(current_price),
                "progress_ratio": float(rep_ratio),
                "signal_desc": str(rep_desc),
                "is_triggered": bool(final_trigger)
            }
            
            return bool(final_trigger)
                        
        except Exception as e:
            saveLog(f">> [매수 판정 에러] {ticker}: {e}")
        return False

    def evaluate_single_sell_condition(self, ticker, strategy_type, current_price, avg_buy_price, breakeven_price):
        """단일 매도(청산) 전략 판정 (본전 이상 이익구간 전제)"""
        try:
            if strategy_type == SellStrategyType.HODL_NO_LOSS:
                return False
                
            # 최고가 관리 업데이트 (이익 구간일 때만 최고가 트래킹 갱신이 check_sell_condition에서 선수행됨)
            if ticker not in self.held_coins_max_price:
                self.held_coins_max_price[ticker] = current_price
            max_price = self.held_coins_max_price[ticker]
            
            # A. 트레일링 스탑
            if strategy_type == SellStrategyType.TRAILING_STOP_NO_LOSS:
                trailing_trigger_price = max_price * (1.0 - self.trailing_stop_ratio)
                if current_price <= trailing_trigger_price and current_price >= breakeven_price:
                    saveLog(f">> [트레일링 스탑 트리거] {ticker} 현재가: {current_price} <= 트리거가: {trailing_trigger_price} (최고가: {max_price})")
                    return True
            
            # B. RSI 과매수 청산 (RSI >= rsi_sell_limit)
            elif strategy_type == SellStrategyType.RSI_OVERBOUGHT:
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=30)
                if df is not None and len(df) >= 15:
                    rsi_val = calculate_rsi_value(df, period=self.rsi_period)
                    if rsi_val >= self.rsi_sell_limit:
                        saveLog(f">> [RSI 과매수 트리거] {ticker} 현재 RSI: {rsi_val:.1f} >= {self.rsi_sell_limit:.1f}")
                        return True
                        
            # C. 볼린저 밴드 상단 터치 청산
            elif strategy_type == SellStrategyType.BB_UPPER_TOUCH:
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=30)
                if df is not None and len(df) >= self.bb_period:
                    upper_band, lower_band = calculate_bb_values(df, period=self.bb_period, std_dev=self.bb_deviation)
                    if current_price >= upper_band:
                        saveLog(f">> [볼린저 상단 터치 트리거] {ticker} 현재가: {current_price} >= BB상단: {upper_band}")
                        return True
                        
            return False
        except Exception as e:
            saveLog(f">> [단일 매도 판정 오류] {ticker} - {strategy_type}: {e}")
            return False

    def check_sell_condition(self, ticker, avg_buy_price, current_price):
        """모듈화된 매도 시점 판정 (다중 전략 AND/OR 결합 및 강제 손절 즉각 집행)"""
        try:
            # 원금 + 수수료 기준 손익분기점 계산
            breakeven_price = avg_buy_price * (1.0 + self.fee_buffer)
            
            # 1. 최우선 강제 손절 (FIXED_STOP_LOSS)
            # sell_strategies에 포함되어 있으면, 손익분기점 미달 여부와 무관하게 손절가 체크
            if SellStrategyType.FIXED_STOP_LOSS in self.sell_strategies:
                stop_loss_price = avg_buy_price * (1.0 + self.fixed_stop_loss_ratio)
                if current_price <= stop_loss_price:
                    saveLog(f">> [고정 손절 트리거] {ticker} 현재가: {current_price} <= 손절가: {stop_loss_price}")
                    return True

            # 2. 본전 미만이면 무조건 매도 차단 (손절 제외)
            if current_price < breakeven_price:
                return False

            # --- 이 하 조건은 본전 이상(이익 구간)인 상황 ---
            
            # 최고가 트래킹 갱신
            if ticker not in self.held_coins_max_price:
                self.held_coins_max_price[ticker] = current_price
            else:
                self.held_coins_max_price[ticker] = max(current_price, self.held_coins_max_price[ticker])
            
            # 평가할 청산 전략 추출 (고정 손절을 제외한 익절 전략들)
            exit_strategies = [s for s in self.sell_strategies if s != SellStrategyType.FIXED_STOP_LOSS]
            if not exit_strategies:
                return False
                
            results = []
            for s in exit_strategies:
                res = self.evaluate_single_sell_condition(ticker, s, current_price, avg_buy_price, breakeven_price)
                results.append(res)
                
            # AND / OR 조합에 따른 매도 최종 판정
            if self.sell_strategy_relation == "AND":
                return all(results)
            else:
                return any(results)
                
        except Exception as e:
            saveLog(f">> [매도 판정 에러] {ticker}: {e}")
        return False

    def get_account_balances(self):
        """계좌 정보 조회 및 보유 자산 계산 (모의/실거래 모드 분기)"""
        balances = {}
        krw = 0.0
        total_assets = 0.0
        
        try:
            if self.trade_mode == "TEST":
                # 모의 투자: 가상 잔고 파일에서 로딩
                acc = self.load_virtual_account()
                krw = float(acc.get("virtual_krw", 1000000.0))
                total_assets = krw
                
                virtual_balances = acc.get("virtual_balances", {})
                for ticker, info in virtual_balances.items():
                    balance = float(info.get('balance', 0))
                    avg_buy_price = float(info.get('avg_buy_price', 0))
                    cur_price = get_current_price(ticker)
                    time.sleep(0.1)
                    val = balance * cur_price
                    total_assets += val
                    
                    # 최고가 관리 및 갱신
                    if ticker not in self.held_coins_max_price:
                        self.held_coins_max_price[ticker] = max(avg_buy_price, cur_price)
                    else:
                        self.held_coins_max_price[ticker] = max(cur_price, self.held_coins_max_price[ticker])
                    max_price = self.held_coins_max_price[ticker]
                    
                    balances[ticker] = {
                        'balance': balance,
                        'avg_buy_price': avg_buy_price,
                        'current_price': cur_price,
                        'value': val,
                        'max_price': max_price
                    }
            else:
                # 실거래: 업비트 거래소 API 호출
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
                        cur_price = get_current_price(ticker)
                        time.sleep(0.1)
                        val = balance * cur_price
                        total_assets += val
                        
                        # 최고가 관리 및 갱신
                        if ticker not in self.held_coins_max_price:
                            self.held_coins_max_price[ticker] = max(avg_buy_price, cur_price)
                        else:
                            self.held_coins_max_price[ticker] = max(cur_price, self.held_coins_max_price[ticker])
                        max_price = self.held_coins_max_price[ticker]
                        
                        balances[ticker] = {
                            'balance': balance,
                            'avg_buy_price': avg_buy_price,
                            'current_price': cur_price,
                            'value': val,
                            'max_price': max_price
                        }
        except Exception as e:
            saveLog(f">> [계좌 조회 에러] {e}")
            
        # 자산 이력 실시간 저장 호출
        if total_assets > 0:
            self.save_assets_history(total_assets)
            
        return krw, total_assets, balances

    def save_assets_history(self, total_assets):
        """자산 총액 이력을 assets_history.json에 누적 저장 (하루 최대 1회, 10분 이내 중복 파일 쓰기 방지)"""
        now = datetime.now()
        
        # 10분 메모리 캐시 검사
        if hasattr(self, "last_history_save_time"):
            if (now - self.last_history_save_time).total_seconds() < 600:
                return
        
        self.last_history_save_time = now
        
        try:
            history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets_history.json")
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except Exception:
                    history = []
            
            now_date_str = now.strftime("%Y-%m-%d")
            
            # 오늘 이미 기록했는지 날짜 기준 중복 검사
            already_recorded = False
            for record in history:
                if record["timestamp"].startswith(now_date_str):
                    # 오늘 날짜 기록이 이미 있으면 업데이트
                    record["total_assets"] = total_assets
                    already_recorded = True
                    break
            
            if not already_recorded:
                # 오늘 첫 기록인 경우 추가
                history.append({
                    "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
                    "total_assets": total_assets
                })
            
            # 데이터 개수 제한 (2000개)
            if len(history) > 2000:
                history = history[-2000:]
                
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f">> [자산 이력 저장 에러] {e}")

    def get_period_returns(self, current_assets):
        """매도 완료 이력을 바탕으로 일, 주, 월, 년 단위 실현 손익 계산"""
        returns = {
            "daily": {"amount": 0.0, "ratio": 0.0, "status": "ok"},
            "weekly": {"amount": 0.0, "ratio": 0.0, "status": "ok"},
            "monthly": {"amount": 0.0, "ratio": 0.0, "status": "ok"},
            "yearly": {"amount": 0.0, "ratio": 0.0, "status": "ok"}
        }
        
        try:
            history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_history.json")
            history = []
            if os.path.exists(history_path):
                with open(history_path, "r", encoding="utf-8") as f:
                    history = json.load(f)
                    
            if not history:
                return returns
                
            now = datetime.now()
            
            periods = {
                "daily": 1,
                "weekly": 7,
                "monthly": 30,
                "yearly": 365
            }
            
            for key, days in periods.items():
                target_date = now - timedelta(days=days)
                period_pl_sum = 0.0
                period_buy_cost_sum = 0.0
                
                for record in history:
                    # 현재 모드(TEST / LIVE)에 맞는 기록만 필터링
                    if record.get("trade_mode", "TEST") != self.trade_mode:
                        continue
                        
                    rec_time = datetime.strptime(record["timestamp"], "%Y-%m-%d %H:%M:%S")
                    if rec_time >= target_date:
                        period_pl_sum += float(record.get("realized_pl", 0.0))
                        period_buy_cost_sum += float(record.get("buy_cost", 0.0))
                
                # 수익률 계산 (기간 내 총 투입 비용 대비 실현 수익)
                ratio = 0.0
                if period_buy_cost_sum > 0:
                    ratio = (period_pl_sum / period_buy_cost_sum) * 100
                
                returns[key] = {
                    "amount": period_pl_sum,
                    "ratio": ratio,
                    "status": "ok"
                }
                
        except Exception as e:
            print(f">> [기간별 실현 손익 계산 에러] {e}")
            
        return returns

    def record_trade_history(self, ticker, avg_buy_price, sell_price, balance):
        """매도 완료 시 실현 손익 이력을 trade_history.json에 기록"""
        try:
            history_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "trade_history.json")
            history = []
            if os.path.exists(history_path):
                try:
                    with open(history_path, "r", encoding="utf-8") as f:
                        history = json.load(f)
                except Exception:
                    history = []
            
            # 수수료 포함 실현 손익 계산 (매수수수료 0.05%, 매도수수료 0.05% 가정)
            buy_cost = avg_buy_price * balance * 1.0005
            sell_revenue = sell_price * balance * 0.9995
            realized_pl = sell_revenue - buy_cost
            
            new_record = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "ticker": ticker,
                "avg_buy_price": avg_buy_price,
                "sell_price": sell_price,
                "balance": balance,
                "buy_cost": buy_cost,
                "sell_revenue": sell_revenue,
                "realized_pl": realized_pl,
                "trade_mode": self.trade_mode
            }
            
            history.append(new_record)
            
            # 최대 10,000개 거래 기록 보존
            if len(history) > 10000:
                history = history[-10000:]
                
            with open(history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
                
            saveLog(f">> [실현 손익 기록 완료] {ticker}: {realized_pl:+.2f}원 확정")
            
        except Exception as e:
            print(f">> [거래 이력 기록 에러] {e}")

    def execute_manual_buy(self, ticker):
        """대시보드로부터 요청된 수동 즉시 매수 집행"""
        try:
            # 1. 이미 보유 중인지 체크
            krw, total_assets, balances = self.get_account_balances()
            if ticker in balances:
                saveLog(f">> [수동 매수 실패] {ticker} 이미 보유 중입니다.")
                return False, "이미 보유 중인 종목입니다."
                
            if krw < 5000:
                return False, "주문 가능 원화 잔고가 부족합니다 (최소 5000원 필요)."
                
            # 2. 매수 예산 산출
            buy_budget_per_coin = total_assets * self.portfolio_ratio
            buy_amount = min(buy_budget_per_coin, self.max_buy_amount, krw)
            
            if buy_amount < 5000:
                buy_amount = min(5000.0, krw) # 최소 주문금액 강제
                
            current_price = get_current_price(ticker)
            if current_price is None or current_price <= 0:
                return False, "현재가를 조회할 수 없습니다."
                
            if self.trade_mode == "TEST":
                # 가상 매수 집행
                acc = self.load_virtual_account()
                # 수수료 0.05% 가산
                actual_spent = buy_amount
                buy_cost_net = actual_spent / 1.0005
                qty = buy_cost_net / current_price
                
                acc["virtual_krw"] = acc.get("virtual_krw", 1000000.0) - actual_spent
                if "virtual_balances" not in acc:
                    acc["virtual_balances"] = {}
                acc["virtual_balances"][ticker] = {
                    "balance": qty,
                    "avg_buy_price": current_price
                }
                self.save_virtual_account(acc)
                
                saveLog(f">> [수동 가상 매수 완료] {ticker} 구매완료 (금액: {buy_amount:.0f}원, 수량: {qty:.6f}, 단가: {current_price})")
                send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [모의] 수동 매수 완료!\n코인: {ticker}\n매수가: {current_price:.2f}\n금액: {buy_amount:.0f}원")
            else:
                # 실거래 매수 주문
                saveLog(f">> [수동 매수 집행] {ticker} 시장가 매수 진행 (금액: {buy_amount}원)")
                self.upbitInst.buy_market_order(ticker, buy_amount)
                send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [실제] 수동 매수 완료!\n코인: {ticker}\n금액: {buy_amount:.0f}원")
                
            # 최고가 트래킹 세팅
            self.held_coins_max_price[ticker] = current_price
            return True, "매수 주문이 성공적으로 집행되었습니다."
            
        except Exception as e:
            saveLog(f">> [수동 매수 에러] {e}")
            return False, str(e)

    def execute_manual_sell(self, ticker):
        """대시보드로부터 요청된 수동 즉시 매도 집행"""
        try:
            # 1. 보유 중인지 체크
            krw, total_assets, balances = self.get_account_balances()
            if ticker not in balances:
                return False, "보유 중인 종목이 아닙니다."
                
            info = balances[ticker]
            qty = info['balance']
            avg_buy_price = info['avg_buy_price']
            current_price = get_current_price(ticker)
            if current_price is None or current_price <= 0:
                current_price = info['current_price'] # 가격 에러 시 캐싱된 현재가 사용
                
            if self.trade_mode == "TEST":
                # 가상 매도 집행
                acc = self.load_virtual_account()
                sell_val = qty * current_price
                # 수수료 0.05% 제하고 회수
                net_revenue = sell_val * 0.9995
                
                acc["virtual_krw"] = acc.get("virtual_krw", 0.0) + net_revenue
                acc["virtual_balances"].pop(ticker, None)
                self.save_virtual_account(acc)
                
                # 실현 손익 기록 저장
                self.record_trade_history(ticker, avg_buy_price, current_price, qty)
                
                saveLog(f">> [수동 가상 매도 완료] {ticker} 전량 매도 완료 (수량: {qty:.6f}, 매도가: {current_price})")
                send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [모의] 수동 매도 완료!\n코인: {ticker}\n평단가: {avg_buy_price:.2f} -> 매도가: {current_price:.2f}")
            else:
                # 실거래 매도 주문
                saveLog(f">> [수동 매도 집행] {ticker} 시장가 전량 매도 진행 (수량: {qty})")
                self.upbitInst.sell_market_order(ticker, qty)
                
                # 실현 손익 기록 저장
                self.record_trade_history(ticker, avg_buy_price, current_price, qty)
                send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [실제] 수동 매도 완료!\n코인: {ticker}\n평단가: {avg_buy_price:.2f} -> 매도가: {current_price:.2f}")
                
            # 최고가 트래킹 제거
            if ticker in self.held_coins_max_price:
                del self.held_coins_max_price[ticker]
                
            return True, "매도 주문이 성공적으로 집행되었습니다."
            
        except Exception as e:
            saveLog(f">> [수동 매도 에러] {e}")
            return False, str(e)

    def run(self):
        saveLog(">> 트레이딩 스레드 루프 진입.")
        
        # 초기 시간 정보 세팅
        init_time_info()
        
        while True:
            try:
                # 1. 실시간 동적 설정 로드
                self.load_settings()
                
                # 1.5. 폭락장 방어 서킷 브레이커 감시 (비트코인 추세 확인)
                if self.use_circuit_breaker:
                    try:
                        btc_df = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=21)
                        if btc_df is not None and len(btc_df) >= 20:
                            btc_ma20 = float(btc_df['close'].rolling(20).mean().iloc[-1])
                            btc_current = get_current_price("KRW-BTC")
                            if btc_current < btc_ma20:
                                if not self.is_circuit_breaker_active:
                                    saveLog(f">> [서킷 브레이커 발동] 비트코인이 1시간 봉 20선({btc_ma20:.0f}) 아래로 하락({btc_current:.0f}). 신규 매수 차단!")
                                self.is_circuit_breaker_active = True
                            else:
                                if self.is_circuit_breaker_active:
                                    saveLog(f">> [서킷 브레이커 해제] 비트코인이 1시간 봉 20선({btc_ma20:.0f}) 위로 복귀({btc_current:.0f}). 신규 매수 재개.")
                                self.is_circuit_breaker_active = False
                        else:
                            self.is_circuit_breaker_active = False
                    except Exception as e:
                        saveLog(f">> [서킷 브레이커 조회 오류] {e}")
                        self.is_circuit_breaker_active = False
                else:
                    self.is_circuit_breaker_active = False
                
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
                        # 매도 집행 분기
                        if self.trade_mode == "TEST":
                            # 모의 투자 매도 시뮬레이션
                            acc = self.load_virtual_account()
                            sell_val = info['balance'] * current_price
                            # 매도 수수료 0.05% 차감 반영
                            acc["virtual_krw"] = acc.get("virtual_krw", 0.0) + (sell_val * 0.9995)
                            acc["virtual_balances"].pop(ticker, None)
                            self.save_virtual_account(acc)
                            
                            # 실현 손익 기록 저장 추가
                            self.record_trade_history(ticker, avg_buy_price, current_price, info['balance'])
                            
                            saveLog(f">> [가상 매도 집행] {ticker} 전량 매도 완료 (수량: {info['balance']:.6f}, 매도가: {current_price})")
                            send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [모의] 매도 완료!!!\n코인: {ticker}\n평단가: {avg_buy_price:.2f} -> 매도가: {current_price:.2f}")
                        else:
                            # 실거래 매도 주문
                            saveLog(f">> [매도 집행] {ticker} 전량 매도 진행 (수량: {info['balance']}, 현재가: {current_price})")
                            self.upbitInst.sell_market_order(ticker, info['balance'])
                            
                            # 실현 손익 기록 저장 추가
                            self.record_trade_history(ticker, avg_buy_price, current_price, info['balance'])
                            
                            send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [실제] 매도 완료!!!\n코인: {ticker}\n평단가: {avg_buy_price:.2f} -> 매도가: {current_price:.2f}")
                        
                        # 트래킹 데이터 삭제
                        if ticker in self.held_coins_max_price:
                            del self.held_coins_max_price[ticker]
                        
                        # 매도 처리 후 즉시 계좌 정보 재반영을 위해 루프 재시작
                        time.sleep(1)
                        break

                # 5. 매수 감시 (보유 한도 미만이고 원화 잔고가 5000원 이상 있을 때만, 서킷 브레이커 감지 시 차단)
                if self.use_circuit_breaker and self.is_circuit_breaker_active:
                    pass
                elif held_count < self.max_coin_count and krw >= 5000:
                    # 실제 매수할 금액 (원화 잔고, 종목당 설정 예산, 최대 매수 제한 금액 중 최소값 선택)
                    actual_buy_amount = min(buy_budget_per_coin, self.max_buy_amount, krw)
                    
                    if actual_buy_amount >= 5000:
                        for ticker in self.universe:
                            # 이미 보유 중이거나 제외 리스트에 있는 코인이면 매수 대상에서 제외
                            if ticker in balances or ticker in self.load_exclude_tickers():
                                continue
                                
                            # 매수 신호 판정
                            if self.check_buy_condition(ticker):
                                # 진입 시점의 현재가 갱신
                                current_price = get_current_price(ticker)
                                time.sleep(0.1)
                                
                                # 매수 집행 분기
                                if self.trade_mode == "TEST":
                                    # 모의 투자 매수 시뮬레이션
                                    acc = self.load_virtual_account()
                                    if acc.get("virtual_krw", 0.0) >= actual_buy_amount:
                                        acc["virtual_krw"] -= actual_buy_amount
                                        # 매수 수수료 0.05% 차감 후 수량 계산
                                        coin_qty = (actual_buy_amount * 0.9995) / current_price
                                        acc["virtual_balances"][ticker] = {
                                            "balance": coin_qty,
                                            "avg_buy_price": current_price
                                        }
                                        self.save_virtual_account(acc)
                                        
                                        saveLog(f">> [가상 매수 집행] {ticker} 시장가 매수 완료 (금액: {actual_buy_amount:.2f}원, 평단가: {current_price})")
                                        send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [모의] 매수 완료!!!\n코인: {ticker}\n매수 금액: {actual_buy_amount:.2f}원 (체결가: {current_price:.2f})")
                                    else:
                                        saveLog(f">> [가상 매수 실패] 원화 잔고 부족")
                                else:
                                    # 실거래 매수 주문
                                    saveLog(f">> [매수 집행] {ticker} 시장가 매수 진행 (금액: {actual_buy_amount})")
                                    self.upbitInst.buy_market_order(ticker, actual_buy_amount * 0.9995)
                                    send_message(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [실제] 매수 완료!!!\n코인: {ticker}\n매수 금액: {actual_buy_amount:.2f}원 (체결가: {current_price:.2f})")
                                
                                # 매수한 코인의 최고가 트래킹 초기화
                                self.held_coins_max_price[ticker] = current_price
                                
                                # 매수 처리 후 즉시 루프 재시작
                                time.sleep(1)
                                break

                # 매 루프 후 출력할 모니터링 로그 (1분 단위 저장)
                current_timestamp = time.time()
                if current_timestamp - self.last_status_time >= 60:
                    self.last_status_time = current_timestamp
                    mode_label = "[모의 투자]" if self.trade_mode == "TEST" else "[실거래]"
                    status_text = f"{mode_label} 자산 총액: {total_assets:.2f}원 | 원화 잔고: {krw:.2f}원 | 보유 종목 수: {held_count}/{self.max_coin_count}\n"
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
                err_msg = traceback.format_exc()
                saveLog(f">> [루프 에러 발생]\n{err_msg}")
                send_message(f"[에러 알림] {self.strategy_name} 루프 예외 발생:\n{e}")
                time.sleep(10)
