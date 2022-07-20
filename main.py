import datetime
import sys
import os
from PyQt5.QtWidgets import *

from Strategy.break_out_range import *
app = QApplication(sys.argv)

break_out_range = BreakOutRange()
break_out_range.start()



app.exec_()

now = datetime.datetime.now()
print("\n[{}] J1 Auto Bitcoin Start !!!!\n".format(now.strftime('%Y-%m-%d %H:%M:%S')))



