import time

import pandas as pd
import pyupbit
import numpy as np
from Api.upbit import *
from Util.db_helper import *

# 용어 설명
'''
[변동성 돌파 공식 Data]
    k  = 돌파 기준 값 
    bor_range = 변동성 돌파 기준 범위 계산, (전일 고가 - 전일 저가) 
    bor_target = open + bor_range(전날) * 매수비율 (k값)
    bor_profit = high > bor_target 보다 크다면 (변동성 돌파 구매) -> close - bor_target        (수익) 
    bor_cum_profit = bor_profit.shift(1) + bor_profit

    # 백 테스트 정보
    - 7일 기준으로 제공 되는 모든 Data를 저장한다.  
    - 변동성 돌파가 이뤄 질 때 해당 날의 이익 액을 계산 한다.
    - 수집 시작날의 목표 가격이 마지막날 종가에 어떻게 변했는지 확인한다.  
    - Todo : 2일 기준 단위로 높은 확률로 수익을 내는 알고리즘을 구성한다. 
    - Todo : 2일 단위의 Data를 모아 별도로 시뮬레이션 할수 있는 테스트 알고리즘을 구현한다. 


[RSI 공식 Data]
Up                      - 전일 가격보다 상승한 날 
Down                    - 전일 가격보다 하락한 날
AU (Average Ups)        - Up들의 평균
AD (Average Downs)      - Down들의 평균
RS (Relative Strength)  - AU를 AD로 나눈값 -> 상대적 강도 . RS 값이 크다는 건 하락폭 보다 상승한 폭이 크다는 것을 의미한다. 
RSI 공식                 - 100 * AU / (AU + AD) -> RSI 는 100에 가까울 수록 상승세가 강하다는 의미이다.
역추세 전략               - RSI 값이 낮은 하락세인 종목을 매수하는 전략

[유니버스 조건]
- 1 coin이 5000원 이상

'''

# universe data 생성
# @ ticker_list: ticker list 전체
# @ k : 변동성 돌파 매수 비율
# @ file_name : data 저장할 db 명
# @ count : 검색할 day수
def make_universe_for_break_out_range(ticker_list, k, file_name, count):
    # OHCLV(open, high, low, close, volume)로 당일 시가, 고가, 저가, 종가, 거래량에 대한 데이터
    df = pd.DataFrame(ticker_list,
                      columns=[
                          'market',  # 0.종목 구분 코드
                          'korean_name',  # 1.한국 이름
                          'english_name',  # 2.영어 이름
                          'opening_price',  # 3.시가
                          'high_price',  # 4.고가
                          'low_price',  # 5.저가
                          'trade_price(close)',  # 6.종가(현재가)
                          'candle_acc_trade_volume',  # 7.거래 량
                          'candle_acc_trade_price',  # 8.거래 가격
                          'date_time',  # 9.날짜
                          'change_price',  # 10.변화액의 절대 값
                          'change_rate',  # 11.변화율의 절대 값
                          'rsi_strategy',  # 12.rsi 전략 구분
                          'au',  # 13.Up들의 평균
                          'ad',  # 14.Down들의 평균
                          'rs',  # 15.au를 ad로 나눈값
                          'rsi',  # 16.rsi는 100에 가까울수록 상승세가 강하다
                          'bor_strategy',  # 17.break out range 전략 구분
                          'bor_range',  # 18.변동성 범위
                          'bor_target_price',  # 19.변동성 돌파 가격
                          'bor_profit',  # 20.수익액
                          'bor_ror',  # 21.수익률
                          'bor_hpr',  # 22.누적 수익률
                          'bor_draw_down',  # 23.Draw Down (누적  최대 값과 현재 hpr 차이 / 누적 최대값 * 100) - (낙폭)
                          'bor_start_target',  # 24.조회 시작 타겟값
                          'bor_end_target',  # 25.조회 최종 종가
                          'bor_cum_profit',  # 26.누적 수익 액
                          'bor_profit_ratio',  # 27.이익 비율 (종가 / 시작 타겟 가 * 100)
                      ])
    for i, value in enumerate(ticker_list):
        cur_df = df.iloc[i, 0]
        df2 = pyupbit.get_ohlcv(df.iloc[i, 0], count=count)  # 7일동안의 원화 시장의 BTC 라는 의미
        for j in range(0, df2.shape[0]):  # shpe 0 은 row , shape 1 은 col - open	high	low	close	volume	value
            if j == 0:
                df.iloc[i, 3] = df2.iloc[j, 0]  # open
                df.iloc[i, 4] = df2.iloc[j, 1]  # high
                df.iloc[i, 5] = df2.iloc[j, 2]  # low
                df.iloc[i, 6] = df2.iloc[j, 3]  # close
                df.iloc[i, 7] = df2.iloc[j, 4]  # volumn - 거래량
                df.iloc[i, 8] = df2.iloc[j, 5]  # value - 거래 가격
                df.iloc[i, 9] = df2.index[j]  # 조회 날짜
                df.iloc[i, 10] = df2.iloc[j, 3] - df2.iloc[j, 0]  # 변경 값 :종가 - 시가
                df.iloc[i, 11] = df2.iloc[j, 3] / df2.iloc[j, 0]  # 변화 율 :종가 / 시가

                df.iloc[i, 18] = 0  # bor range
                df.iloc[i, 19] = 0  # bor_target_price
                df.iloc[i, 20] = 0  # bor_profit
                df.iloc[i, 21] = 1  # ror - 수익률
                df.iloc[
                    i, 26] = 0  # bor_profit = high > bor_target 보다 크다면 (변동성 돌파 구매) -> close - bor_target        (수익)
            else:
                df.iloc[i, 3] = "{},{}".format(df.iloc[i, 3], df2.iloc[j, 0])  # open
                df.iloc[i, 4] = "{},{}".format(df.iloc[i, 4], df2.iloc[j, 1])  # high
                df.iloc[i, 5] = "{},{}".format(df.iloc[i, 5], df2.iloc[j, 2])  # low
                df.iloc[i, 6] = "{},{}".format(df.iloc[i, 6], df2.iloc[j, 3])  # close
                df.iloc[i, 7] = "{},{}".format(df.iloc[i, 7], df2.iloc[j, 4])  # volumn - 거래량
                df.iloc[i, 8] = "{},{}".format(df.iloc[i, 8], df2.iloc[j, 5])  # value - 거래 가격
                df.iloc[i, 9] = "{},{}".format(df.iloc[i, 9], df2.index[j])  # 조회 날짜
                df.iloc[i, 10] = "{},{}".format(df.iloc[i, 10], df2.iloc[j, 3] - df2.iloc[j, 0])  # 변경 값 :종가 - 시가
                df.iloc[i, 11] = "{},{}".format(df.iloc[i, 11], df2.iloc[j, 3] / df2.iloc[j, 0])  # 변경 값 :종가 / 시가

                bor_target = df2.iloc[j, 0] + (df2.iloc[j - 1, 1] - df2.iloc[j - 1, 2]) * k

                df.iloc[i, 18] = "{},{}".format(df.iloc[i, 18], (df2.iloc[j - 1, 1] - df2.iloc[j - 1, 2]))  # bor_range
                df.iloc[i, 19] = "{},{}".format(df.iloc[i, 19], bor_target)  # bor_target_price

                ror = 0
                if df2.iloc[j, 1] > bor_target:  # high > bor_target
                    bor_profit = df2.iloc[j, 3] - bor_target
                    ror = df2.iloc[j, 3] / bor_target - 0.0005
                else:
                    bor_profit = 0
                    ror = 1

                df.iloc[i, 20] = "{},{}".format(df.iloc[i, 20], bor_profit)  # bor_profit
                df.iloc[i, 21] = "{},{}".format(df.iloc[i, 21], ror)  # ror - 수익률

                df.iloc[i, 26] = df.iloc[i, 26] + bor_profit

        open_data = df.iloc[i, 3]
        str_open = open_data.split(',')
        close_data = df.iloc[i, 6]
        str_close = close_data.split(',')
        target_price_data = df.iloc[i, 19]
        str_target_price = target_price_data.split(',')

        # 종가 / 시작 타겟 가 * 100)
        df.iloc[i, 27] = float(str_close[len(str_close) - 1]) / float(str_target_price[1]) * 100

        # rsi 전략 구분
        df.iloc[i, 12] = "|"

        # au / ad

        au = 0
        au_cnt = 0
        ad = 0
        ad_cnt = 0
        prev_val = 0

        # --- 전체 기준 au , ad, rs, rsi
        for val in str_open:
            value = float(val)
            if value > prev_val:
                au = au + value
                au_cnt = au_cnt + 1
            else:
                ad = ad + value
                ad_cnt = ad_cnt + 1
            prev_val = value
        # au
        if au_cnt == 0:
            df.iloc[i, 13] = 0
        else:
            df.iloc[i, 13] = au / au_cnt  # au 즉가 값의 평균
        # ad
        if ad_cnt == 0:
            df.iloc[i, 14] = 0
        else:
            df.iloc[i, 14] = ad / ad_cnt  # au 즉가 값의 평균
        # rs
        if ad == 0:
            df.iloc[i, 15] = au
        else:
            df.iloc[i, 15] = au / ad  # rs 즉가 값의 평균

        df.iloc[i, 16] = 100 * au / (au + ad)  # rs 즉가 값의 평균

        # bor 전략 구분
        df.iloc[i, 17] = "|"

        # wait
        time.sleep(0.1)

    # bor start, end price 추가
    for i, value in enumerate(ticker_list):
        # hpr 누적곱
        rorData = str.split(df.iloc[i, 21], ',')
        result = 1
        hprMax = 0
        for j, value in enumerate(rorData):
            if j == 0:
                df.iloc[i, 22] = result  # hpr - 누적 수익률
                hprMax = result;
                dd = (hprMax - result) / hprMax * 100
                df.iloc[i, 23] = dd  # Draw Down 계산
            else:
                result = float(rorData[j]) * result
                df.iloc[i, 22] = "{},{}".format(df.iloc[i, 22], result)  # hpr - 누적 수익률
                if result > hprMax:
                    hprMax = result

                dd = (hprMax - result) / hprMax * 100
                df.iloc[i, 23] = "{},{}".format(df.iloc[i, 23], dd)  # Draw Down 계산

        # 21. bor_start
        data = str.split(df.iloc[i, 19], ',')
        df.iloc[i, 24] = float(data[1])  # 두번째 부터 매매

        # 22. bor_end
        data = str.split(df.iloc[i, 6], ',')
        df.iloc[i, 25] = float(data[-1])

    # save research Data
    df.to_excel("{}_{}.xlsx".format(file_name, count))
    if check_table_exist("bitcoin", "{}_{}".format(file_name, count)):
        clear_table_db("bitcoin", "{}_{}".format(file_name, count))

    insert_df_to_db("bitcoin", "{}_{}".format(file_name, count), df)
    sql = "select * from {}".format("{}_{}".format(file_name, count))
    cur = execute_sql("bitcoin", sql)
    #print(cur.fetchall())


## 낙폭 치를 이용한 Rank 계상
def cal_drawdown_rank(data_dic):
    print("calculate Rank Start ! : cnt - {}".format(len(data_dic)))
    rank_data_dic = {}
    rank_dic_dic = {}
    cal_dic = {}
    print(data_dic)

    # 1. Check cal days
    day_cnt = 0
    for key in data_dic:
        data = str.split(data_dic[key], ',')
        day_cnt = len(data)
        break
    print("day cnt : {}".format(day_cnt))
    rank_data_dic = data_dic

    for i in range(0, day_cnt - 1):
        cal_dic = {}
        rank_dic = {}
        for key in rank_data_dic:
            data = str.split(data_dic[key], ',')
            if i == 0:
                if 0 < float(data[day_cnt - (1 + i)]):
                    cal_dic[key] = float(data[day_cnt - (1 + i)])
                    rank_dic[key] = data_dic[key]
            else:
                if 0 < float(data[day_cnt - (1 + i)]) and float(data[day_cnt - (1 + i)]) < float(
                        data[day_cnt - (0 + i)]):
                    cal_dic[key] = float(data[day_cnt - (0 + i)]) - float(data[day_cnt - (1 + i)])
                    rank_dic[key] = data_dic[key]
        rank_data_dic = rank_dic
        sorted_dict = sorted(cal_dic.items(), key=(lambda item: item[1]), reverse=True)
        print(sorted_dict)
        df = pd.DataFrame(sorted_dict)
        rank_dic_dic[i] = sorted_dict

    dd = dict(reversed(list(rank_dic_dic.items())))
    real_rank = {}
    for i in dd:
        for data_dic in dd[i]:
            if not data_dic[0] in real_rank:
                real_rank[data_dic[0]] = data_dic[1]
            else:
                print("is key {}".format(data_dic[0]))

    df = pd.DataFrame(list(real_rank))
    print(len(list(real_rank)))
    return list(real_rank)


def get_universe_drawdown_rank(search_day, rank_cnt):
    # 1. get db data
    sql = "select market, bor_draw_down from " \
          "(select * from {} where bor_start_target < 5000)" \
        .format('universe_{}'.format(search_day))
    cur = execute_sql("bitcoin", sql)
    curData = cur.fetchall()  # list [('KRW-MTL', '0.0,0.0,0.0,0.0'),...]

    # 1. data 정리 -> dictionary {'KRW-MTL': '0.0,0.0,0.0,0.0'...}
    data_dic = {}
    for i, value in curData:
        data_dic[i] = value

    # 2. draw down rank 계산
    return cal_drawdown_rank(data_dic)[0:rank_cnt]

if __name__ == "__main__":
    # ===== make Data =======#
    ticker_data = get_ticker("KRW", False, False, True)
    #
    # make_universe_for_break_out_range(ticker_data, 0.5, "universe", 7)
    # make_universe_for_break_out_range(ticker_data, 0.5, "universe", 6)
    make_universe_for_break_out_range(ticker_data, 0.5, "universe", 5)
    # make_universe_for_break_out_range(ticker_data, 0.5, "universe", 4)
    # make_universe_for_break_out_range(ticker_data, 0.5, "universe", 3)
    # make_universe_for_break_out_range(ticker_data, 0.5, "universe", 2)

    # ===== Simulation ======#
    ranklist = get_universe_drawdown_rank(5, 5)
    print(ranklist)