# PLC 모니터 — 한 번에 클릭 실행

더블클릭 한 번으로 서버 실행 + 브라우저 열기.

---

## Linux

**사용자에게 줄 때**: **plc_test 폴더 전체**만 전달.

**실행 방법**:
1. plc_test 폴더를 열고 **PLC모니터.sh** 더블클릭 → "실행" 또는 "터미널에서 실행" 선택 → 서버 뜨고 브라우저 열림.
2. 그때 **바탕화면에 'PLC 모니터' 아이콘**이 생김. 다음부터는 **바탕화면 아이콘만 더블클릭**하면 됨 (웹 열림).

브라우저가 안 열리면 터미널에 나온 **http://localhost:6005** 를 브라우저에 입력하면 됨.

`start.sh`가 venv·npm·프론트 빌드가 없으면 자동으로 한 뒤 한 포트(6005)에서 서빙함.

**단일 실행파일로 빌드** (배포용):
```bash
./scripts/build-linux.sh
```
→ `dist/PLC모니터` 생성. 그다음에 바탕화면 아이콘 쓰고 싶으면 `./scripts/create-desktop-shortcut.sh` (선택).

---

## Windows .exe 빌드

Windows PC에서만 가능. Node.js + Python 3.8+ 설치 후:

```batch
cd frontend
npm install
node node_modules\vite\bin\vite.js build
cd ..
xcopy /e /i /y frontend\dist backend\frontend_dist
pip install pyinstaller
pyinstaller --noconfirm backend\plc_app.spec
```

→ `dist\PLC모니터.exe` 생성. 더블클릭 시 서버 + 브라우저 열림.

---

## 참고

- **개발**: `./scripts/run.sh` — 프론트(6173) + 백엔드(6005) 동시.
- **한 번에 실행**: **PLC모니터.sh** 더블클릭, 또는 바탕화면의 PLC 모니터 아이콘 (또는 `./scripts/start.sh`).
