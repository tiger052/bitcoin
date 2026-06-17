# 자동 매매 시스템 보안 및 API 키 관리 지침 가이드

본 문서는 자동 매매 프로그램의 API 키 및 SNS 토큰 등 민감한 인증 정보를 안전하게 보존하고 외부(GitHub 등) 노출을 방지하기 위한 보안 가이드라인입니다.

---

## 1. 보안 핵심 원칙

> [!WARNING]
> **API 키의 외부 노출은 자산 탈취로 직결됩니다.**
> * 절대로 `.py` 소스 코드나 Git으로 업로드되는 설정 파일에 API 키 또는 메신저 토큰을 하드코딩하지 마십시오.
> * 실수로라도 API 키가 포함된 파일이 GitHub 등 원격 저장소에 Push되면, 자동 스캔 봇에 의해 단 몇 초 만에 탈취될 수 있습니다.

---

## 2. 기밀 정보 로컬 보관 구조 (`secrets.json`)

자동 매매에 사용되는 모든 중요 인증 정보는 프로젝트 루트 폴더나 소스 코드에서 완전히 격리된 로컬 전용 설정 파일 [secrets.json](file:///d:/workspace/jae1soft/bitcoin/b_dev/bitcoin_server/secrets.json)에서 관리합니다.

### 기밀 파일 구성 템플릿
```json
{
  "upbit_access_key": "YOUR_UPBIT_ACCESS_KEY",
  "upbit_secret_key": "YOUR_UPBIT_SECRET_KEY",
  "telegram_api_token": "YOUR_TELEGRAM_API_TOKEN",
  "telegram_chat_id": "YOUR_TELEGRAM_CHAT_ID",
  "line_api_token": "YOUR_LINE_API_TOKEN"
}
```

### 소스 코드에서의 호출 구조
* 프로그램 진입 시 [const.py](file:///d:/workspace/jae1soft/bitcoin/b_dev/bitcoin_server/Util/const.py) 모듈이 실행되면서 로컬 경로의 `secrets.json` 파일을 파싱하여 글로벌 변수로 바인딩합니다.
* 파일이 없을 시 자동으로 기본 구조의 `secrets.json` 파일을 자동 생성해 기입을 안내합니다.

---

## 3. Git 노출 방지 (`.gitignore` 설정)

프로젝트 루트 디렉토리의 [.gitignore](file:///d:/workspace/jae1soft/bitcoin/.gitignore) 파일을 통해 민감 정보가 깃 원격 서버로 푸시되는 것을 차단하고 있습니다.

### 설정 항목
```text
# 기밀 인증 정보 차단
b_dev/bitcoin_server/secrets.json
*upbit_setting.json
*kakao_setting.json

# 캐시 및 로그 차단
__pycache__/
*.pyc
b_dev/bitcoin_server/Log/*.log
```

---

## 4. API 키 관리 수칙 (업비트 설정)

업비트 Open API 설정 페이지에서 API 키를 발급 및 관리할 때 반드시 준수해야 하는 규칙입니다.

1. **IP 주소 제한 설정 (필수)**: 
   * API 키에 대해 **"특정 IP만 허용"** 옵션을 반드시 활성화하고, 자동 매매 프로그램이 동작하는 PC 또는 서버(AWS 등)의 고정 IP만 등록하십시오.
   * 이렇게 설정하면 설령 API 키가 유출되더라도 외부 IP에서의 무단 요청은 거래소 수준에서 차단됩니다.
2. **출금 권한 해제**:
   * API 키 권한 설정 중 **"출금 권한"**은 절대 활성화하지 마십시오. 
   * 오직 **"조회"** 및 **"주문(매수/매도)"** 권한만 허용해야 프로그램 오류 또는 해킹 발생 시 자산이 외부로 무단 출금되는 사고를 원천 방어할 수 있습니다.
3. **주기적 키 교체**:
   * 최소 3~6개월 단위로 기존 API 키를 폐기하고 새로운 키로 재발급받아 교체 적용하는 것을 권장합니다.

---

## 5. 키 유출 시 비상 대처 요령

만약 API 키나 텔레그램 토큰 등이 외부 또는 GitHub 커밋 이력에 잘못 노출되었음이 확인된 즉시 아래의 조치를 집행해야 합니다.

1. **거래소 API 즉시 삭제**:
   * 업비트 로그인 후 `마이페이지 > Open API 관리`로 즉시 이동하여 유출이 의심되는 API 키 항목을 **삭제(폐기)** 처리하십시오.
2. **메신저 토큰 재발급**:
   * Telegram `@BotFather`를 통해 `/revoke` 명령어를 실행하고 유출된 봇의 API Token을 재생성(무효화) 하십시오.
   * Line Notify 채널에서도 기존 생성된 등록 토큰을 폐기(Disconnect)하고 재발급받으십시오.
3. ** secrets.json 정보 갱신**:
   * 새로 발급받은 기밀 정보를 로컬 `secrets.json` 파일에 반영한 뒤 프로그램을 재시동하십시오.
