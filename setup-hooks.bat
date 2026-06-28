@echo off
cd /d "%~dp0"
git config core.hooksPath .githooks
echo Git hooks installed (.githooks/pre-commit).
echo Blocked from commit: .env, config.json, logs/, __pycache__, *.pem, *.key
pause
