import os
import sys
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add bitcoin_server path to sys.path for importing pyupbit
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(os.path.join(project_root, "bitcoin_server"))

import pyupbit
from Util.make_up_universe import get_high_volume_drawdown_universe

class StrategyBacktester:
    def __init__(self, period_days, start_krw, buy_strategies, buy_strategy_relation,
                 sell_strategies, sell_strategy_relation, portfolio_ratio, max_coin_count,
                 max_buy_amount, trailing_stop_ratio, fixed_stop_loss_ratio, universe_size,
                 use_circuit_breaker=False, rsi_period=14, rsi_buy_limit=30.0, rsi_sell_limit=70.0,
                 bb_period=20, bb_deviation=2.0):
        self.period_days = period_days
        self.start_krw = start_krw
        
        # 하위 호환을 위해 단일 문자열이 인입되는 경우 리스트로 래핑
        if isinstance(buy_strategies, str):
            self.buy_strategies = [buy_strategies]
        else:
            self.buy_strategies = buy_strategies if buy_strategies else ["MA5_CROSSOVER"]
            
        self.buy_strategy_relation = buy_strategy_relation if buy_strategy_relation else "OR"
        
        if isinstance(sell_strategies, str):
            self.sell_strategies = [sell_strategies]
        else:
            self.sell_strategies = sell_strategies if sell_strategies else ["TRAILING_STOP_NO_LOSS"]
            
        self.sell_strategy_relation = sell_strategy_relation if sell_strategy_relation else "OR"
        
        self.portfolio_ratio = portfolio_ratio
        self.max_coin_count = max_coin_count
        self.max_buy_amount = max_buy_amount
        self.trailing_stop_ratio = trailing_stop_ratio
        self.fixed_stop_loss_ratio = fixed_stop_loss_ratio
        self.universe_size = universe_size
        self.use_circuit_breaker = use_circuit_breaker
        self.rsi_period = rsi_period
        self.rsi_buy_limit = rsi_buy_limit
        self.rsi_sell_limit = rsi_sell_limit
        self.bb_period = bb_period
        self.bb_deviation = bb_deviation

    def get_candidate_tickers(self):
        """백테스트 대상이 될 상위 거래대금 코인 추출"""
        try:
            # 24시간 거래대금 상위 universe 리스트 가져오기
            tickers = get_high_volume_drawdown_universe(top_n=max(30, self.universe_size * 2), select_count=self.universe_size)
            if not tickers:
                # Fallback list if API fails
                tickers = ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP", "KRW-DOGE", "KRW-ADA", "KRW-AVAX", "KRW-DOT", "KRW-LINK", "KRW-TRX"]
            return tickers[:self.universe_size]
        except Exception as e:
            print(f"Error getting candidate tickers: {e}")
            return ["KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP", "KRW-DOGE"]

    def run_simulation(self):
        """백테스트 실행"""
        # 1. 대상 티커 로드
        tickers = self.get_candidate_tickers()
        
        # 2. 각 티커별 1시간 봉 캔들 데이터 다운로드
        candle_data = {}
        count = 24 * self.period_days + 48 # 지표 연산 버퍼용 여유분 넉넉히 추가
        
        print(f"Downloading historical candles for {len(tickers)} tickers...")
        for ticker in tickers:
            try:
                df = pyupbit.get_ohlcv(ticker, interval="minute60", count=count)
                if df is not None and not df.empty:
                    # MA5 계산
                    df['ma5'] = df['close'].rolling(5).mean()
                    
                    # Custom RSI 계산
                    delta = df['close'].diff()
                    up = delta.clip(lower=0)
                    down = -delta.clip(upper=0)
                    ema_up = up.ewm(com=self.rsi_period - 1, adjust=False).mean()
                    ema_down = down.ewm(com=self.rsi_period - 1, adjust=False).mean()
                    rs = ema_up / (ema_down + 1e-10)
                    df['rsi'] = 100 - (100 / (1 + rs))
                    
                    # Custom Bollinger Bands 계산
                    sma = df['close'].rolling(window=self.bb_period).mean()
                    std = df['close'].rolling(window=self.bb_period).std()
                    df['bb_upper'] = sma + (self.bb_deviation * std)
                    df['bb_lower'] = sma - (self.bb_deviation * std)
                    
                    candle_data[ticker] = df
                time.sleep(0.15) # API Rate Limit 방지
            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")

        # 2.5. 비트코인(KRW-BTC) 캔들 데이터 다운로드 (서킷 브레이커 감시용)
        btc_candles = None
        if self.use_circuit_breaker:
            try:
                print("Downloading historical BTC candles for Circuit Breaker...")
                btc_candles = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=count)
                if btc_candles is not None and not btc_candles.empty:
                    btc_candles['ma20'] = btc_candles['close'].rolling(20).mean()
            except Exception as e:
                print(f"Error fetching BTC data for circuit breaker: {e}")

        if not candle_data:
            raise Exception("시세 데이터를 하나도 수집하지 못해 백테스트를 실행할 수 없습니다.")

        # 3. 시간축 정렬 (모든 데이터 프레임의 공통 인덱스를 오름차순으로 확보)
        all_timestamps = set()
        for df in candle_data.values():
            all_timestamps.update(df.index)
            
        sorted_timestamps = sorted(list(all_timestamps))
        # 버퍼용 20시간 건너뛰고 시뮬레이션 시작
        start_idx = max(20, self.bb_period)
        if len(sorted_timestamps) <= start_idx:
            raise Exception("백테스트를 위한 데이터가 부족합니다.")
            
        sim_timestamps = sorted_timestamps[start_idx:]

        # 4. 시뮬레이션 변수 초기화
        krw = self.start_krw
        positions = {} # { ticker: { qty, buy_price, buy_time, max_price } }
        trades = [] # [ { ticker, buy_time, buy_price, sell_time, sell_price, return_rate, profit } ]
        
        equity_curve = []
        max_total_assets = self.start_krw
        mdd = 0.0

        print(f"Running simulation over {len(sim_timestamps)} hours...")
        
        for t_idx, ts in enumerate(sim_timestamps):
            # 실시간 평가자산 계산
            total_eval_assets = krw
            for ticker, pos in positions.items():
                df = candle_data[ticker]
                if ts in df.index:
                    cur_price = df.loc[ts, 'close']
                    total_eval_assets += pos['qty'] * cur_price
                else:
                    total_eval_assets += pos['qty'] * pos['buy_price']
            
            # MDD 계산
            max_total_assets = max(max_total_assets, total_eval_assets)
            drawdown = (max_total_assets - total_eval_assets) / max_total_assets * 100
            mdd = max(mdd, drawdown)
            
            equity_curve.append({
                "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S"),
                "total_assets": total_eval_assets
            })

            # A. 매도(청산) 조건 체크
            closed_tickers = []
            for ticker, pos in positions.items():
                df = candle_data[ticker]
                if ts not in df.index:
                    continue
                
                row = df.loc[ts]
                high = row['high']
                low = row['low']
                close = row['close']
                
                # 최고가 갱신
                pos['max_price'] = max(pos['max_price'], high)
                
                # 1. 고정 손절선 체크 (수수료 차감 고려 - 관계식과 상관없이 즉시 집행)
                stop_loss_trigger = False
                if "FIXED_STOP_LOSS" in self.sell_strategies:
                    stop_loss_price = pos['buy_price'] * (1.0 + self.fixed_stop_loss_ratio)
                    if low <= stop_loss_price:
                        sell_price = stop_loss_price
                        stop_loss_trigger = True
                        
                # 2. 트레일링 스탑 및 기타 익절 전략 체크 (AND / OR)
                trailing_trigger = False
                if not stop_loss_trigger:
                    breakeven_price = pos['buy_price'] * 1.0015
                    
                    eval_sells = [s for s in self.sell_strategies if s != "FIXED_STOP_LOSS"]
                    if eval_sells:
                        sell_results = []
                        for s_type in eval_sells:
                            if s_type == "HODL_NO_LOSS":
                                sell_results.append(False)
                            elif s_type == "TRAILING_STOP_NO_LOSS":
                                trailing_stop_price = pos['max_price'] * (1.0 - self.trailing_stop_ratio)
                                is_trail = low <= trailing_stop_price and close >= breakeven_price
                                sell_results.append(is_trail)
                                if is_trail:
                                    sell_price = trailing_stop_price
                            elif s_type == "RSI_OVERBOUGHT":
                                is_rsi_ok = not pd.isna(row['rsi']) and row['rsi'] >= self.rsi_sell_limit and close >= breakeven_price
                                sell_results.append(is_rsi_ok)
                                if is_rsi_ok:
                                    sell_price = close
                            elif s_type == "BB_UPPER_TOUCH":
                                is_bb_ok = not pd.isna(row['bb_upper']) and high >= row['bb_upper'] and close >= breakeven_price
                                sell_results.append(is_bb_ok)
                                if is_bb_ok:
                                    sell_price = max(row['bb_upper'], row['open'])
                        
                        if self.sell_strategy_relation == "AND":
                            trailing_trigger = all(sell_results)
                        else:
                            trailing_trigger = any(sell_results)
                        
                # 청산 실행
                if stop_loss_trigger or trailing_trigger:
                    qty = pos['qty']
                    gross_revenue = qty * sell_price
                    net_revenue = gross_revenue * 0.9995 # 수수료 0.05% 차감
                    
                    krw += net_revenue
                    profit = net_revenue - (pos['buy_price'] * qty * 1.0005) # 매수수수료 포함 원금 대비
                    return_rate = (sell_price / pos['buy_price'] - 1.0) * 100
                    
                    trades.append({
                        "ticker": ticker,
                        "buy_time": pos['buy_time'].strftime("%Y-%m-%d %H:%M:%S"),
                        "buy_price": float(pos['buy_price']),
                        "sell_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
                        "sell_price": float(sell_price),
                        "return_rate": float(return_rate),
                        "profit": float(profit)
                    })
                    
                    closed_tickers.append(ticker)
                    
            for ticker in closed_tickers:
                del positions[ticker]

            # B. 매수(진입) 조건 체크
            # 서킷 브레이커 감시 체크 (비트코인이 1시간 봉 20선 미만인지 판단)
            is_btc_down = False
            if self.use_circuit_breaker and btc_candles is not None and ts in btc_candles.index:
                btc_row = btc_candles.loc[ts]
                if not pd.isna(btc_row['ma20']) and btc_row['close'] < btc_row['ma20']:
                    is_btc_down = True

            if is_btc_down:
                pass # 비트코인 급락 추세 시 신규 진입 차단
            elif len(positions) < self.max_coin_count and krw >= 5000:
                # 종목당 균등 예산 산정
                buy_budget_per_coin = self.start_krw * self.portfolio_ratio
                buy_amount = min(buy_budget_per_coin, self.max_buy_amount, krw)
                
                if buy_amount >= 5000:
                    for ticker in tickers:
                        # 이미 보유 중이거나 데이터가 없는 코인 제외
                        if ticker in positions or ticker not in candle_data:
                            continue
                            
                        df = candle_data[ticker]
                        if ts not in df.index:
                            continue
                            
                        # ts에 해당하는 위치 인덱스 찾기
                        idx_loc = df.index.get_loc(ts)
                        if idx_loc < 3:
                            continue
                            
                        row = df.iloc[idx_loc]
                        prev_row = df.iloc[idx_loc - 1]
                        
                        # 다중 매수 전략 판정
                        buy_results = []
                        for s_type in self.buy_strategies:
                            if s_type == "MA5_CROSSOVER":
                                if not pd.isna(row['ma5']) and not pd.isna(prev_row['ma5']):
                                    buy_results.append(row['close'] > row['ma5'] and prev_row['close'] <= prev_row['ma5'])
                                else:
                                    buy_results.append(False)
                            elif s_type == "CANDLE_3_GREEN":
                                buy_results.append(row['close'] > row['open'] and 
                                                   prev_row['close'] > prev_row['open'] and 
                                                   df.iloc[idx_loc - 2]['close'] > df.iloc[idx_loc - 2]['open'])
                            elif s_type == "OPEN_BREAKOUT":
                                open_of_day = None
                                for lookback in range(24):
                                    check_idx = idx_loc - lookback
                                    if check_idx < 0:
                                        break
                                    check_ts = df.index[check_idx]
                                    if check_ts.hour == 9:
                                        open_of_day = df.iloc[check_idx]['open']
                                        break
                                if open_of_day is not None and open_of_day > 0:
                                    buy_results.append(row['high'] >= open_of_day * 1.015)
                                else:
                                    buy_results.append(False)
                            elif s_type == "RSI_OVERSOLD":
                                buy_results.append(not pd.isna(row['rsi']) and row['rsi'] <= self.rsi_buy_limit)
                            elif s_type == "BB_LOWER_TOUCH":
                                buy_results.append(not pd.isna(row['bb_lower']) and row['low'] <= row['bb_lower'])
                            else:
                                buy_results.append(False)
                                
                        if not buy_results:
                            signal = False
                        elif self.buy_strategy_relation == "AND":
                            signal = all(buy_results)
                        else:
                            signal = any(buy_results)

                        # 진입 처리
                        if signal:
                            close_price = float(row['close'])
                            actual_spent = buy_amount
                            buy_cost_net = actual_spent / 1.0005 # 수수료 0.05% 선제 반영
                            qty = buy_cost_net / close_price
                            
                            positions[ticker] = {
                                "qty": qty,
                                "buy_price": close_price,
                                "buy_time": ts,
                                "max_price": close_price
                            }
                            
                            krw -= actual_spent
                            
                            # 보유 한도 다 채웠으면 매수 루프 종료
                            if len(positions) >= self.max_coin_count or krw < 5000:
                                break

        # 5. 시뮬레이션 완료 후 남은 포지션 평가 청산
        last_ts = sim_timestamps[-1]
        for ticker, pos in list(positions.items()):
            df = candle_data[ticker]
            close_price = df.loc[last_ts, 'close'] if last_ts in df.index else pos['buy_price']
            
            qty = pos['qty']
            gross_revenue = qty * close_price
            net_revenue = gross_revenue * 0.9995
            
            krw += net_revenue
            profit = net_revenue - (pos['buy_price'] * qty * 1.0005)
            return_rate = (close_price / pos['buy_price'] - 1.0) * 100
            
            trades.append({
                "ticker": ticker,
                "buy_time": pos['buy_time'].strftime("%Y-%m-%d %H:%M:%S"),
                "buy_price": float(pos['buy_price']),
                "sell_time": last_ts.strftime("%Y-%m-%d %H:%M:%S"),
                "sell_price": float(close_price),
                "return_rate": float(return_rate),
                "profit": float(profit)
            })

        # 6. 통계 도출
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t['profit'] > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        final_assets = krw
        total_profit = final_assets - self.start_krw
        return_ratio = (final_assets / self.start_krw - 1.0) * 100

        # 최신 순 정렬
        trades.sort(key=lambda x: x['sell_time'], reverse=True)

        return {
            "period_days": self.period_days,
            "start_krw": float(self.start_krw),
            "final_assets": float(final_assets),
            "total_profit": float(total_profit),
            "return_ratio": float(return_ratio),
            "total_trades": int(total_trades),
            "win_rate": float(win_rate),
            "mdd": float(mdd),
            "trades": trades
        }

if __name__ == "__main__":
    # 간단 작동 테스트
    tester = StrategyBacktester(
        period_days=7,
        start_krw=1000000,
        buy_strategy="MA5_CROSSOVER",
        sell_strategy="TRAILING_STOP_NO_LOSS",
        portfolio_ratio=0.1,
        max_coin_count=5,
        max_buy_amount=100000,
        trailing_stop_ratio=0.02,
        fixed_stop_loss_ratio=-0.03,
        universe_size=10
    )
    res = tester.run_simulation()
    print("Test finished. Return Ratio:", res["return_ratio"])
