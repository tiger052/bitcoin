import datetime
import sys
import os
import threading
from Strategy.break_out_range import *


break_out_range = BreakOutRange()
break_out_range.start()

now = datetime.datetime.now()
print("\n[{}] J1 Auto Bitcoin Start !!!!\n".format(now.strftime('%Y-%m-%d %H:%M:%S')))



