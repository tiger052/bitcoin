import pyupbit
import numpy as np

# OHCLV(open, high, low, close, volume)로 당일 시가, 고가, 저가, 종가, 거래량에 대한 데이터 
df = pyupbit.get_ohlcv("KRW-ETH",count = 7)     #7일동안의 원화 시장의 BTC 라는 의미

# 변동성 돌파 기준 범위 계산, (고가 - 저가) * k값
df['range'] = (df['high'] - df['low']) * 0.5    

# range 컬럼을 한칸씩 밑으로 내림(.shift(1))
df['target'] = df['open'] + df['range'].shift(1)    #

fee = 0 #수수료 fee = 0.0032

# np.where(조건문, 참일때 값, 거짓일때 값)
df['ror'] = np.where(df['high'] > df['target'],             # 고가가 타겟 보다 높으면 
                     df['close'] / df['target'] - fee,      # 종가 / 타겟
                     1)

# 누적 곱 계산(cumprod) => 누적 수익률
df['hpr'] = df['ror'].cumprod()

# Draw Down 계산 (누적  최대 값과 현재 hpr 차이 / 누적 최대값 * 100)
df['dd'] = (df['hpr'].cummax() - df['hpr']) / df['hpr'].cummax() * 100

# MDD 계산 (낙폭)
print("MDD(%): ", df['dd'].max())

# 엑셀로 출력
print(df)
df.to_excel("dd.xlsx")
