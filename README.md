# PLC UDP Monitor

PLC에서 전송하는 UDP 데이터를 실시간으로 모니터링하는 웹 애플리케이션입니다.

## 환경 세팅 (최초 1회)

프론트엔드/백엔드를 실행하기 전에 아래 중 한 가지 방법으로 환경을 세팅하세요.

### 방법 A: 스크립트로 한 번에 세팅

**필수 (실행 전 설치)**
- Python 3.8+  
  - Debian/Ubuntu: `sudo apt install python3 python3-venv` (또는 `python3.12-venv`)
- Node.js 18+, npm (프론트엔드): `sudo apt install nodejs npm`

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

- 백엔드: `backend/venv` 가상환경을 만들고 `requirements.txt` 설치
- 프론트엔드: `frontend/node_modules` 설치 (`npm install`)
- Node가 없으면 백엔드만 세팅되고, 프론트는 설치 후 `cd frontend && npm install` 실행

### 방법 B: 수동 세팅

**백엔드**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**프론트엔드** (Node.js 설치 후)

```bash
cd frontend
npm install
```

---

## 실행 방법

터미널 **두 개**에서 각각 실행하세요. (백엔드를 먼저 켠 뒤 프론트 실행 권장)

#### 1. 백엔드 (Flask, 포트 6005)

```bash
./run-backend.sh
```

또는 수동:

```bash
cd backend
source venv/bin/activate  # Windows: venv\Scripts\activate
python app.py
```

#### 2. 프론트엔드 (React, 포트 6173)

새 터미널에서:

```bash
./run-frontend.sh
```

또는 수동:

```bash
cd frontend
npm run dev
```

종료: 각 터미널에서 `Ctrl+C`

### 주의: `ERR_CONNECTION_REFUSED` /api/events

프론트엔드만 실행하고 백엔드를 켜지 않으면 **서버 연결 끊김**이 뜨고 콘솔에 `GET http://localhost:6005/api/events net::ERR_CONNECTION_REFUSED`가 나옵니다.  
**해결:** 먼저 `./run-backend.sh`로 백엔드를 실행한 뒤, 다른 터미널에서 `./run-frontend.sh`로 프론트를 실행하세요.

### 사용 방법

1. 브라우저에서 `http://localhost:6173` 접속
2. **바인딩 IP**: UDP 수신에 사용할 IP (기본: `0.0.0.0` - 모든 인터페이스)
3. **포트**: 수신할 UDP 포트 (기본: `5212`)
4. **UDP 연결** 버튼 클릭
5. PLC에서 해당 IP:Port로 데이터 전송 시 실시간으로 표시됩니다.
