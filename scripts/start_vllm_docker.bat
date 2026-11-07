@echo off
REM ================================================================
REM Quick Launcher for vLLM with Qwen2.5-7B-Instruct using Docker
REM Optimized for NVIDIA GeForce RTX 3060 (12GB VRAM)
REM ================================================================

echo ================================================================
echo    STARTING VLLM DOCKER CONTAINER FOR QWEN2.5-7B-INSTRUCT
echo ================================================================

REM Check if Docker is running
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker Desktop is not running!
    echo Please start Docker Desktop on Windows first, then re-run this script.
    pause
    exit /b 1
)

echo [INFO] Docker Desktop is running.
echo [INFO] Launching vLLM container (vllm/vllm-openai:latest)...
echo [INFO] GPU Memory Utilization: 85%% (~10.2 GB VRAM)
echo [INFO] Model: Qwen/Qwen2.5-7B-Instruct
echo ----------------------------------------------------------------

docker run -d --name vllm-qwen ^
  --gpus all ^
  -p 8000:8000 ^
  --ipc=host ^
  -v vllm_huggingface_cache:/root/.cache/huggingface ^
  --restart unless-stopped ^
  vllm/vllm-openai:latest ^
  --model Qwen/Qwen2.5-7B-Instruct ^
  --host 0.0.0.0 ^
  --port 8000 ^
  --gpu-memory-utilization 0.85 ^
  --max-model-len 8192

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Container 'vllm-qwen' has been started successfully!
    echo Endpoint: http://localhost:8000/v1
    echo To view logs in real-time, run: docker logs -f vllm-qwen
) else (
    echo.
    echo [WARNING] Failed to start container via docker run.
    echo Attempting via docker compose...
    docker compose -f docker-compose.vllm.yml up -d
)

echo ================================================================
pause
