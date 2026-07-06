@echo off
REM ILLIP launcher — type `illip` in any terminal.
REM   illip                   -> start the web app + open it in the browser (normal chat)
REM   illip code              -> terminal coding agent in a fresh window (serious work)
REM   illip code --continue   -> resume your last terminal conversation
REM   illip build "make X"    -> run the agent crew on a folder
REM   illip status / version  -> other subcommands
set "ILLIPDIR=E:\Projects\ILLIP_AI"
set "PY=%ILLIPDIR%\.venv\Scripts\python.exe"

REM No arguments -> start the server + open the browser.
if "%~1"=="" goto :serve

REM `illip code` -> open a CLEAN new terminal window running the agent. The new
REM window inherits YOUR current folder as its working dir (we don't cd here),
REM so it builds where you are. PYTHONPATH lets Python find the app package.
if /i "%~1"=="code" (
    set "PYTHONPATH=%ILLIPDIR%"
    start "ILLIP Code" cmd /k "%PY% -m app.cli %*"
    goto :eof
)

REM other subcommands run inline
cd /d "%ILLIPDIR%"
"%PY%" -m app.cli %*
goto :eof

:serve
cd /d "%ILLIPDIR%"
netstat -ano | findstr ":8000 " | findstr LISTENING >nul 2>&1
if errorlevel 1 (
    echo Starting ILLIP...
    start "ILLIP" /min "%PY%" -m uvicorn app.main:app --port 8000
    timeout /t 5 /nobreak >nul
) else (
    echo ILLIP already running.
)
start "" "http://localhost:8000"
