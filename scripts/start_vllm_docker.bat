@echo off
REM ================================================================
REM Quick Launcher for vLLM with Qwen2.5-7B-Instruct-GPTQ-Int4 (Docker)
REM Highly Optimized for NVIDIA RTX 3060 (12GB VRAM):
REM - ~5.5 GB VRAM utilized
REM - Safe KV Cache memory allocation
REM ================================================================

REM Ensure working directory is project root
cd /d "%~dp0.."

echo ================================================================
echo    STARTING VLLM DOCKER: Qwen2.5-7B-Instruct-GPTQ-Int4
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
echo [INFO] Model: Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4
echo [INFO] GPU Memory Utilization: 70%%
echo [INFO] Max Context Length: 4096 tokens
echo ----------------------------------------------------------------

docker run -d --name vllm-qwen ^
  --gpus all ^
  -p 8000:8000 ^
  --ipc=host ^
  -v vllm_huggingface_cache:/root/.cache/huggingface ^
  --restart unless-stopped ^
  vllm/vllm-openai:latest ^
  Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4 ^
  --host 0.0.0.0 ^
  --port 8000 ^
  --gpu-memory-utilization 0.70 ^
  --max-model-len 4096

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Container 'vllm-qwen' has been started!
    echo Endpoint: http://localhost:8000/v1
    echo To follow logs: docker logs -f vllm-qwen
) else (
    echo.
    echo [WARNING] Attempting launch via docker compose...
    docker compose -f docker-compose.vllm.yml up -d
)

echo ================================================================
pause
