"""
Diagnostic and Test script for vLLM Serving + Qwen2.5-7B-Instruct-GPTQ-Int4.

Usage:
  python scripts/test_vllm_connection.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.config import config
from etl.llm_client import LLMClient

def main():
    print("=" * 65)
    print("  VLLM SERVING & QWEN2.5-7B-INSTRUCT-GPTQ-INT4 CONNECTION TEST  ")
    print("=" * 65)
    print(f"Target API Endpoint : {config.llm_api_base}")
    print(f"Target Model Name   : {config.llm_model_name}")
    print("-" * 65)

    client = LLMClient()
    available = client.is_service_available()

    if available:
        print("[SUCCESS] vLLM Docker server is ACTIVE and REACHABLE!")
        print("Sending a warm-up prompt to Qwen2.5-7B-Instruct-GPTQ-Int4...")
        try:
            res = client.chat_completion(
                messages=[{"role": "user", "content": "Xin chao, ban la ai va co the giup gi cho Groupware IQ NFFICE?"}],
                max_tokens=100
            )
            print("\nResponse from Qwen2.5-7B-Instruct-GPTQ-Int4:")
            print(res)
            print("-" * 65)
        except Exception as e:
            print(f"[ERROR] Failed to generate response: {e}")
    else:
        print("[STATUS] vLLM server is currently OFFLINE / NOT RUNNING.")
        print(f"Cannot connect to {config.llm_api_base}.")
        print("\nTo start vLLM with Docker, do the following:")
        print("-----------------------------------------------------------------")
        print("1. Ensure Docker Desktop is running.")
        print("2. Run the quick launcher script:")
        print("   scripts\\start_vllm_docker.bat")
        print("   OR run via Docker Compose:")
        print("   docker compose -f docker-compose.vllm.yml up -d")
        print("3. Check download/startup progress:")
        print("   docker logs -f vllm-qwen")
        print("-----------------------------------------------------------------")

    print("=" * 65)

if __name__ == "__main__":
    main()
