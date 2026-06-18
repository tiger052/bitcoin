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

class LoginRequest(BaseModel):
    username: str
    password: str

class ConfigRequest(BaseModel):
    trade_mode: str
    buy_strategy: str
    sell_strategy: str
    portfolio_ratio: float
    max_coin_count: int
    max_buy_amount: float
    trailing_stop_ratio: float
    fixed_stop_loss_ratio: float
    fee_buffer: float

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
        
        # 로그 파일 최신 15줄 읽기
        log_path = os.path.join(project_root, "bitcoin_server", "Log", "output.log")
        logs = []
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
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
            "universe": strategy_instance.universe,
            "max_buy_amount": strategy_instance.max_buy_amount,
            "max_coin_count": strategy_instance.max_coin_count,
            "portfolio_ratio": strategy_instance.portfolio_ratio,
            "trailing_stop_ratio": strategy_instance.trailing_stop_ratio,
            "fixed_stop_loss_ratio": strategy_instance.fixed_stop_loss_ratio,
            "fee_buffer": strategy_instance.fee_buffer,
            "logs": logs
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            "fee_buffer": config_data.fee_buffer
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=2)
            
        return {"status": "success", "message": "Configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
