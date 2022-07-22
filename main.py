import datetime
import threading
from Strategy.break_out_range import *

now = datetime.now()
print("\n[{}] J1 Auto Bitcoin Start !!!!\n".format(now.strftime('%Y-%m-%d %H:%M:%S')))

# 전략 설정
break_out_range = BreakOutRange()
break_out_range.start()





