@echo off
rem Starts the trade-in bot. Extra arguments are passed through,
rem e.g.  start_bot.bat --mode trade --dry-run
cd /d "%~dp0"
python trade_in_bot.py %*
pause
