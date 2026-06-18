import sys
import os
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

# 웹 서버 연동 및 실행 (0.0.0.0:5000 바인딩)
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.append(os.path.join(project_root, "web_server"))
    
    import web_server
    import uvicorn
    
    # 웹 서버 백엔드에 매매 전략 인스턴스 주입
    web_server.strategy_instance = drawdown_holding
    
    def run_web_server():
        uvicorn.run("web_server:app", host="0.0.0.0", port=5000, log_level="warning")
        
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()
    print(">> 웹 모니터링 대시보드 서버 가동 완료 (포트: 5000)")
except Exception as e:
    print(f">> 웹 서버 구동 에러: {e}")




