@echo off
REM ILLIP launcher — type `illip` in any terminal.
REM   illip                   -> chat with ILLIP in the terminal (like a local coding agent)
REM   illip --continue        -> resume your last terminal conversation
REM   illip build "make X" -d .  -> run the agent crew on a folder
REM   illip start             -> start the web server + UI (browser)
REM   illip status / version  -> other subcommands
cd /d "E:\Projects\ILLIP_AI"
".venv\Scripts\python.exe" -m app.cli %*
