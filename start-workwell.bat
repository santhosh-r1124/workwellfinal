@echo off
REM Starts WorkWell AI with Docker Desktop and opens it in the browser.
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
  echo Docker Desktop is not installed. Install it from https://www.docker.com/products/docker-desktop/ and run this again.
  pause
  exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
  echo Starting Docker Desktop...
  start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  for /l %%i in (1,1,60) do (
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1 && goto docker_ready
  )
  echo Docker Desktop did not start. Open it manually, wait until it says "Engine running", then run this again.
  pause
  exit /b 1
)
:docker_ready

if not exist .env copy .env.example .env >nul

echo Building and starting WorkWell AI (first run takes a few minutes)...
docker compose up -d --build
if errorlevel 1 (
  echo Docker could not start the app. See the messages above.
  pause
  exit /b 1
)

echo Waiting for the backend to load data...
for /l %%i in (1,1,100) do (
  curl -s http://localhost:8000/health/ready | findstr /c:"\"ready\"" >nul && goto backend_ready
  timeout /t 3 /nobreak >nul
)
echo The backend is still starting. Check it with:  docker compose logs backend
:backend_ready

start "" http://localhost:3300
echo.
echo WorkWell AI is running at http://localhost:3300
echo To stop it later run:  docker compose down
pause
