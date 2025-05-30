@echo off
cd C:\ngrok
ngrok http --url=exotic-broadly-eel.ngrok-free.app 8000 --request-header-remove ngrok-skip-browser-warning
pause

