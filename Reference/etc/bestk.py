import pyupbit
import numpy as np

# 가장 좋은 k를 구하는 방법
def get_ror(k=0.5):
    df = pyupbit.get_ohlcv("KRW-BTC",count=7)
    df['range'] = (df['high'] - df['low']) * k
    df['target'] = df['open'] + df['range'].shift(1)

    fee = 0.0032
    df['ror'] = np.where(df['high'] > df['target'],
                         df['close'] / df['target'] - fee,
                         1)

    ror = df['ror'].cumprod()[-2]
    return ror


for k in np.arange(0.1, 1.0, 0.07):
    ror = get_ror(k)
    print("%.2f %f" % (k, ror))


    