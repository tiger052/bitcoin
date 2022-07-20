from datetime import *

def check_transaction_open():
    """현재 시간이 거래 시간인지 확인하는 함수 (당일 9:00 ~ 다음날 8:50)"""
    now = datetime.now()
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = now.replace(day=now.day+1, hour=8, minute=50, second=0, microsecond=0)
    return start_time <= now <= end_time

def check_adjacent_transaction_closed():
    """현재 시간이 마감 종료 부근인지 확인하는 함수(매수 시간 확인용)"""
    now = datetime.now()
    base_time = now.replace(hour=8, minute=51, second=0, microsecond=0)
    end_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    return base_time <= now < end_time

if __name__ == "__main__":
    check_adjacent_transaction_closed()
