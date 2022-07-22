from datetime import *

def check_transaction_open():
    """현재 시간이 거래 시간인지 확인하는 함수 (당일 9:00 ~ 다음날 8:45)"""
    now = datetime.now()
    start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    end_time = now.replace(day=now.day+1, hour=8, minute=45, second=0, microsecond=0)
    return start_time <= now <= end_time

def check_adjacent_transaction_closed():
    """현재 시간이 마감 종료 부근인지 확인하는 함수(매수 시간 확인용)"""
    now = datetime.now()
    base_time = now.replace(hour=8, minute=51, second=0, microsecond=0)
    end_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
    return base_time <= now < end_time

def get_transaction_close_time():
    """현재 시간이 거래 시간인지 확인하는 함수 (당일 9:00 ~ 다음날 8:45)"""
    now = datetime.now()
    end_time = now.replace(hour=8, minute=59, second=59, microsecond=0)
    return end_time

def check_one_minute_time():
    """분 단위인지 체크 """
    now = datetime.now()
    return now.strftime('%S') == '00'

def check_thirty_minute_time():
    """30분 단위인지 체크 """
    now = datetime.now()
    return now.strftime('%M') == '30' and now.strftime('%S') == '00'

def check_on_time():
    """정시 체크"""
    now = datetime.now()
    return now.strftime('%M') == '00' and now.strftime('%S') == '00'

def check_last_time():
    """하루 마감 마지막 시간 체크"""
    now = datetime.now()
    return now.strftime('%H:%M:%S') == "08:59:59"

if __name__ == "__main__":
    check_adjacent_transaction_closed()
