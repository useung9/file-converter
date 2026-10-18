@echo off
echo [FileConvert] 패키지 설치 중...
pip install -r requirements.txt
echo.
echo [FileConvert] 서버 시작 중... http://localhost:8080
python main.py
pause
