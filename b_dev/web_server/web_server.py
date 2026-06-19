import os
import sys
import uuid
import json
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException, Response, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 설정 로드를 위한 경로 확보
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
# bitcoin_server 경로 추가
sys.path.append(os.path.join(project_root, "bitcoin_server"))

# FastAPI 앱 설정 및 static 폴더 연동
app = FastAPI()
static_dir = os.path.join(current_dir, "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 거래 스레드 참조 변수 (main.py에서 할당 예정)
strategy_instance = None

# 활성 세션 메모리 저장소
ACTIVE_SESSIONS = set()

from typing import List, Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class ManualTradeRequest(BaseModel):
    ticker: str

class ConfigRequest(BaseModel):
    trade_mode: str
    buy_strategy: Optional[str] = "MA5_CROSSOVER"
    sell_strategy: Optional[str] = "TRAILING_STOP_NO_LOSS"
    portfolio_ratio: float
    max_coin_count: int
    max_buy_amount: float
    trailing_stop_ratio: float
    fixed_stop_loss_ratio: float
    fee_buffer: float
    universe_size: int
    # 고도화 매개변수 추가
    use_circuit_breaker: bool = False
    rsi_period: int = 14
    rsi_buy_limit: float = 30.0
    rsi_sell_limit: float = 70.0
    bb_period: int = 20
    bb_deviation: float = 2.0
    buy_strategies: List[str] = ["MA5_CROSSOVER"]
    buy_strategy_relation: str = "OR"
    sell_strategies: List[str] = ["TRAILING_STOP_NO_LOSS"]
    sell_strategy_relation: str = "OR"

class ExcludeTickerRequest(BaseModel):
    ticker: str

class BacktestRequest(BaseModel):
    period_days: int
    start_krw: float
    buy_strategy: Optional[str] = "MA5_CROSSOVER"
    sell_strategy: Optional[str] = "TRAILING_STOP_NO_LOSS"
    portfolio_ratio: float
    max_coin_count: int
    max_buy_amount: float
    trailing_stop_ratio: float
    fixed_stop_loss_ratio: float
    universe_size: int
    # 고도화 매개변수 추가
    use_circuit_breaker: bool = False
    rsi_period: int = 14
    rsi_buy_limit: float = 30.0
    rsi_sell_limit: float = 70.0
    bb_period: int = 20
    bb_deviation: float = 2.0
    buy_strategies: List[str] = ["MA5_CROSSOVER"]
    buy_strategy_relation: str = "OR"
    sell_strategies: List[str] = ["TRAILING_STOP_NO_LOSS"]
    sell_strategy_relation: str = "OR"

class NotificationSettings(BaseModel):
    sns_type: str
    telegram_api_token: Optional[str] = ""
    telegram_chat_id: Optional[str] = ""
    line_api_token: Optional[str] = ""
    discord_webhook_url: Optional[str] = ""

def load_web_credentials():
    """secrets.json에서 웹 로그인용 아이디/비밀번호 로드"""
    secrets_path = os.path.join(project_root, "bitcoin_server", "secrets.json")
    username = "admin"
    password = "adminpassword" # 기본 패스워드
    
    try:
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            username = data.get("web_username", "admin")
            password = data.get("web_password", "adminpassword")
    except Exception as e:
        print(f"Error loading web credentials: {e}")
    return username, password

def get_current_user(request: Request):
    """쿠키 세션 검증 의존성"""
    session_id = request.cookies.get("session_id")
    if not session_id or session_id not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return "admin"

@app.get("/")
def read_root(request: Request):
    """루트 주소 접속 시 로그인 상태에 따라 대시보드 또는 로그인 페이지로 리다이렉트"""
    session_id = request.cookies.get("session_id")
    if session_id in ACTIVE_SESSIONS:
        return RedirectResponse(url="/static/index.html")
    return RedirectResponse(url="/static/login.html")

@app.post("/api/login")
def login(login_data: LoginRequest, response: Response):
    """로그인 처리 및 세션 쿠키 발급"""
    valid_username, valid_password = load_web_credentials()
    
    if login_data.username == valid_username and login_data.password == valid_password:
        session_id = uuid.uuid4().hex
        ACTIVE_SESSIONS.add(session_id)
        # 1일간 유효한 세션 쿠키 설정
        response.set_cookie(key="session_id", value=session_id, max_age=86400, httponly=True)
        return {"status": "success", "message": "Login successful"}
    
    raise HTTPException(status_code=400, detail="Invalid username or password")

@app.post("/api/logout")
def logout(request: Request, response: Response):
    """로그아웃 처리 및 세션 쿠키 삭제"""
    session_id = request.cookies.get("session_id")
    if session_id in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS.remove(session_id)
    response.delete_cookie(key="session_id")
    return {"status": "success"}

@app.get("/api/status")
def get_status(user: str = Depends(get_current_user)):
    """현재 거래 상태, 자산 현황, 로그 데이터 취합 반환"""
    if strategy_instance is None:
        return {"status": "error", "message": "Trading engine is not running"}
        
    try:
        # 실시간 자산 및 잔고 조회
        krw, total_assets, balances = strategy_instance.get_account_balances()
        
        # 기간별 투자 수익 계산
        period_returns = strategy_instance.get_period_returns(total_assets)
        
        # 감시 제외 코인 목록 로드
        exclude_tickers = []
        exclude_path = os.path.join(project_root, "bitcoin_server", "exclude_tickers.json")
        if os.path.exists(exclude_path):
            try:
                with open(exclude_path, "r", encoding="utf-8") as f:
                    exclude_tickers = json.load(f)
            except Exception:
                pass

        # 감시 대상 목록 필터링
        filtered_universe = [t for t in strategy_instance.universe if t not in exclude_tickers]
        
        # 로그 파일 최신 15줄 읽기
        log_path = os.path.join(project_root, "bitcoin_server", "Log", "output.log")
        logs = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                # 최신 15줄 필터링하여 리스트업
                logs = [line.strip() for line in lines[-25:] if line.strip()]
                
        return {
            "trade_mode": strategy_instance.trade_mode,
            "buy_strategy": strategy_instance.buy_strategy_type.value,
            "sell_strategy": strategy_instance.sell_strategy_type.value,
            "krw": krw,
            "total_assets": total_assets,
            "balances": balances,
            "universe": filtered_universe,
            "universe_status": strategy_instance.universe_status,
            "universe_size": strategy_instance.universe_size,
            "ticker_names": getattr(strategy_instance, "ticker_names", {}),
            "universe_drawdowns": getattr(strategy_instance, "universe_drawdowns", {}),
            "max_buy_amount": strategy_instance.max_buy_amount,
            "max_coin_count": strategy_instance.max_coin_count,
            "portfolio_ratio": strategy_instance.portfolio_ratio,
            "trailing_stop_ratio": strategy_instance.trailing_stop_ratio,
            "fixed_stop_loss_ratio": strategy_instance.fixed_stop_loss_ratio,
            "fee_buffer": strategy_instance.fee_buffer,
            "period_returns": period_returns,
            "logs": logs,
            "exclude_tickers": exclude_tickers,
            
            # 신규 고도화 매개변수 추가 반환
            "use_circuit_breaker": getattr(strategy_instance, "use_circuit_breaker", False),
            "is_circuit_breaker_active": getattr(strategy_instance, "is_circuit_breaker_active", False),
            "rsi_period": getattr(strategy_instance, "rsi_period", 14),
            "rsi_buy_limit": getattr(strategy_instance, "rsi_buy_limit", 30.0),
            "rsi_sell_limit": getattr(strategy_instance, "rsi_sell_limit", 70.0),
            "bb_period": getattr(strategy_instance, "bb_period", 20),
            "bb_deviation": getattr(strategy_instance, "bb_deviation", 2.0),
            "buy_strategies": [s.value for s in getattr(strategy_instance, "buy_strategies", [])],
            "buy_strategy_relation": getattr(strategy_instance, "buy_strategy_relation", "OR"),
            "sell_strategies": [s.value for s in getattr(strategy_instance, "sell_strategies", [])],
            "sell_strategy_relation": getattr(strategy_instance, "sell_strategy_relation", "OR")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trade_history")
def get_trade_history(user: str = Depends(get_current_user)):
    """최근 청산 완료된 거래 내역 조회 (최대 50건)"""
    history_path = os.path.join(project_root, "bitcoin_server", "trade_history.json")
    if not os.path.exists(history_path):
        return []
        
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
            
        # 최신 순 정렬 후 상위 50개 반환
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return history[:50]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/manual_buy")
def manual_buy(trade_data: ManualTradeRequest, user: str = Depends(get_current_user)):
    """수동 즉시 매수 집행"""
    if strategy_instance is None:
        raise HTTPException(status_code=500, detail="Trading engine is not running")
        
    success, message = strategy_instance.execute_manual_buy(trade_data.ticker)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "success", "message": message}

@app.post("/api/manual_sell")
def manual_sell(trade_data: ManualTradeRequest, user: str = Depends(get_current_user)):
    """수동 즉시 매도 집행"""
    if strategy_instance is None:
        raise HTTPException(status_code=500, detail="Trading engine is not running")
        
    success, message = strategy_instance.execute_manual_sell(trade_data.ticker)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "success", "message": message}

@app.post("/api/config")
def update_config(config_data: ConfigRequest, user: str = Depends(get_current_user)):
    """웹 화면에서 제출된 대시보드 설정을 strategy_setting.json에 동적 반영"""
    config_path = os.path.join(project_root, "bitcoin_server", "strategy_setting.json")
    
    try:
        new_config = {
            "trade_mode": config_data.trade_mode,
            "buy_strategy": config_data.buy_strategy,
            "sell_strategy": config_data.sell_strategy,
            "portfolio_ratio": config_data.portfolio_ratio,
            "max_coin_count": config_data.max_coin_count,
            "max_buy_amount": config_data.max_buy_amount,
            "trailing_stop_ratio": config_data.trailing_stop_ratio,
            "fixed_stop_loss_ratio": config_data.fixed_stop_loss_ratio,
            "fee_buffer": config_data.fee_buffer,
            "universe_size": config_data.universe_size,
            
            # 신규 파라미터들 저장
            "use_circuit_breaker": config_data.use_circuit_breaker,
            "rsi_period": config_data.rsi_period,
            "rsi_buy_limit": config_data.rsi_buy_limit,
            "rsi_sell_limit": config_data.rsi_sell_limit,
            "bb_period": config_data.bb_period,
            "bb_deviation": config_data.bb_deviation,
            "buy_strategies": config_data.buy_strategies,
            "buy_strategy_relation": config_data.buy_strategy_relation,
            "sell_strategies": config_data.sell_strategies,
            "sell_strategy_relation": config_data.sell_strategy_relation
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2)
            
        # 즉시 트레이딩 엔진 메모리에 반영
        if strategy_instance is not None:
            strategy_instance.load_settings()
            
        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset_test")
def reset_test(user: str = Depends(get_current_user)):
    """가상 자산(모의 투자) 잔고를 100만 원으로 초기화"""
    if strategy_instance is None:
        raise HTTPException(status_code=500, detail="Trading engine is not running")
        
    try:
        # 가상 계좌 초기화 데이터 구성
        acc = {
            "virtual_krw": 1000000.0,
            "virtual_balances": {}
        }
        strategy_instance.save_virtual_account(acc)
        # 봇의 최고가 트래킹 정보도 함께 리셋
        strategy_instance.held_coins_max_price = {}
        
        # 비동기적으로 저장 로그 호출
        import sys
        sys.path.append(os.path.join(project_root, "bitcoin_server"))
        from Util.file_helper import saveLog
        saveLog(f">> [가상 자산 초기화] 사용자가 대시보드에서 모의 투자 잔고를 초기화했습니다.")
        
        return {"status": "success", "message": "Virtual account reset successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/assets_history")
def get_assets_history(user: str = Depends(get_current_user)):
    """자산 총액 이력 조회"""
    history_path = os.path.join(project_root, "bitcoin_server", "assets_history.json")
    if not os.path.exists(history_path):
        return []
    try:
        with open(history_path, "r", encoding="utf-8") as f:
            history = json.load(f)
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/exclude_tickers")
def get_exclude_tickers(user: str = Depends(get_current_user)):
    """제외 종목 조회"""
    exclude_path = os.path.join(project_root, "bitcoin_server", "exclude_tickers.json")
    if not os.path.exists(exclude_path):
        return []
    try:
        with open(exclude_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/exclude_ticker")
def add_exclude_ticker(req_data: ExcludeTickerRequest, user: str = Depends(get_current_user)):
    """제외 종목 등록"""
    exclude_path = os.path.join(project_root, "bitcoin_server", "exclude_tickers.json")
    try:
        exclude_list = []
        if os.path.exists(exclude_path):
            with open(exclude_path, "r", encoding="utf-8") as f:
                exclude_list = json.load(f)
        
        if req_data.ticker not in exclude_list:
            exclude_list.append(req_data.ticker)
            with open(exclude_path, "w", encoding="utf-8") as f:
                json.dump(exclude_list, f, indent=2, ensure_ascii=False)
                
        return {"status": "success", "message": f"{req_data.ticker}가 제외 목록에 추가되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/exclude_ticker")
def remove_exclude_ticker(req_data: ExcludeTickerRequest, user: str = Depends(get_current_user)):
    """제외 종목 삭제"""
    exclude_path = os.path.join(project_root, "bitcoin_server", "exclude_tickers.json")
    try:
        exclude_list = []
        if os.path.exists(exclude_path):
            with open(exclude_path, "r", encoding="utf-8") as f:
                exclude_list = json.load(f)
        
        if req_data.ticker in exclude_list:
            exclude_list.remove(req_data.ticker)
            with open(exclude_path, "w", encoding="utf-8") as f:
                json.dump(exclude_list, f, indent=2, ensure_ascii=False)
                
        return {"status": "success", "message": f"{req_data.ticker}가 제외 목록에서 제거되었습니다."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backtest")
def run_backtest(req_data: BacktestRequest, user: str = Depends(get_current_user)):
    """전략 백테스트 시뮬레이션 실행"""
    try:
        sys.path.append(os.path.join(project_root, "bitcoin_server", "Strategy"))
        from backtester import StrategyBacktester
        
        tester = StrategyBacktester(
            period_days=req_data.period_days,
            start_krw=req_data.start_krw,
            buy_strategies=req_data.buy_strategies,
            buy_strategy_relation=req_data.buy_strategy_relation,
            sell_strategies=req_data.sell_strategies,
            sell_strategy_relation=req_data.sell_strategy_relation,
            portfolio_ratio=req_data.portfolio_ratio,
            max_coin_count=req_data.max_coin_count,
            max_buy_amount=req_data.max_buy_amount,
            trailing_stop_ratio=req_data.trailing_stop_ratio,
            fixed_stop_loss_ratio=req_data.fixed_stop_loss_ratio,
            universe_size=req_data.universe_size,
            use_circuit_breaker=req_data.use_circuit_breaker,
            rsi_period=req_data.rsi_period,
            rsi_buy_limit=req_data.rsi_buy_limit,
            rsi_sell_limit=req_data.rsi_sell_limit,
            bb_period=req_data.bb_period,
            bb_deviation=req_data.bb_deviation
        )
        
        result = tester.run_simulation()
        return result
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications")
def get_notifications(user: str = Depends(get_current_user)):
    """현재 저장된 디스코드/텔레그램 알림 정보 조회"""
    secrets_path = os.path.join(project_root, "bitcoin_server", "secrets.json")
    if not os.path.exists(secrets_path):
        return {
            "sns_type": "Telegram",
            "telegram_api_token": "",
            "telegram_chat_id": "",
            "line_api_token": "",
            "discord_webhook_url": ""
        }
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "sns_type": data.get("sns_type", "Telegram"),
            "telegram_api_token": data.get("telegram_api_token", ""),
            "telegram_chat_id": data.get("telegram_chat_id", ""),
            "line_api_token": data.get("line_api_token", ""),
            "discord_webhook_url": data.get("discord_webhook_url", "")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications")
def save_notifications(settings: NotificationSettings, user: str = Depends(get_current_user)):
    """디스코드/텔레그램 알림 정보를 secrets.json에 저장 및 라이브 반영"""
    secrets_path = os.path.join(project_root, "bitcoin_server", "secrets.json")
    try:
        data = {}
        if os.path.exists(secrets_path):
            with open(secrets_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
        # 필드 덮어쓰기
        data["sns_type"] = settings.sns_type
        data["telegram_api_token"] = settings.telegram_api_token
        data["telegram_chat_id"] = settings.telegram_chat_id
        data["line_api_token"] = settings.line_api_token
        data["discord_webhook_url"] = settings.discord_webhook_url
        
        with open(secrets_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            
        # const 모듈의 load_secrets를 재로드하여 라이브 엔진에 즉시 반영
        sys.path.append(os.path.join(project_root, "bitcoin_server"))
        import Util.const as const
        const.load_secrets()
        
        return {"status": "success", "message": "Notification settings saved and reloaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notifications/test")
def test_notification(settings: NotificationSettings, user: str = Depends(get_current_user)):
    """입력받은 설정을 기반으로 테스트 알림 즉시 송신 시도"""
    try:
        sys.path.append(os.path.join(project_root, "bitcoin_server"))
        from Util.notifier import send_message_telegram, send_message_line, send_message_discord
        
        test_msg = "🔔 [J1 Auto Bitcoin] 테스트 알림 전송에 성공했습니다!"
        
        if settings.sns_type == "Telegram":
            if not settings.telegram_api_token or not settings.telegram_chat_id:
                raise HTTPException(status_code=400, detail="텔레그램 토큰 및 채팅 ID를 모두 입력해주세요.")
            send_message_telegram(test_msg, settings.telegram_chat_id, settings.telegram_api_token)
        elif settings.sns_type == "Line":
            if not settings.line_api_token:
                raise HTTPException(status_code=400, detail="라인 API 토큰을 입력해주세요.")
            send_message_line(test_msg, settings.line_api_token)
        elif settings.sns_type == "Discord":
            if not settings.discord_webhook_url:
                raise HTTPException(status_code=400, detail="디스코드 웹훅 URL을 입력해주세요.")
            send_message_discord(test_msg, settings.discord_webhook_url)
        else:
            raise HTTPException(status_code=400, detail="유효하지 않은 알림 타입입니다.")
            
        return {"status": "success", "message": "테스트 알림 전송 성공!"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"테스트 전송 실패: {str(e)}")
