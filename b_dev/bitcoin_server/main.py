import datetime
import threading
from Strategy.break_out_range_base import *
from Strategy.drawdown_holding_strategy import *

now = datetime.now()
print("\n[{}] J1 Auto Bitcoin Start !!!!\n".format(now.strftime('%Y-%m-%d %H:%M:%S')))

# 전략 설정 (기존 변동성 돌파 전략 대신 신규 낙폭 과대 반등 및 익절 보존 전략 가동)
# break_out_range = BreakOutRange()
# break_out_range.start()

drawdown_holding = DrawdownHoldingStrategy()
drawdown_holding.start()




