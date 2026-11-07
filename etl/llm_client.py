"""
LLM Client Module for vLLM Serving (OpenAI-compatible).
Provides seamless integration between Groupware Graph Ontology, Qdrant Vector DB,
and Qwen2.5-7B-Instruct running on vLLM.
"""

import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from etl.config import config

logger = logging.getLogger("chatbot.llm_client")

class LLMClient:
    def __init__(self, api_base: Optional[str] = None, model_name: Optional[str] = None):
        self.api_base = api_base or config.llm_api_base
        self.model_name = model_name or config.llm_model_name
        self.client = OpenAI(
            base_url=self.api_base,
            api_key=config.llm_api_key
        )

    def is_service_available(self) -> bool:
        """Checks if the vLLM server is up and reachable."""
        try:
            models = self.client.models.list()
            return any(self.model_name in m.id or m.id in self.model_name for m in models.data) or len(models.data) > 0
        except Exception as e:
            logger.debug(f"vLLM server check failed: {e}")
            return False

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """Sends chat completion request to vLLM server."""
        temp = temperature if temperature is not None else config.llm_temperature
        tokens = max_tokens if max_tokens is not None else config.llm_max_tokens

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temp,
                max_tokens=tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling vLLM API at {self.api_base}: {e}")
            raise

    def rag_answer(
        self,
        user_query: str,
        graph_facts: List[str],
        vector_passages: List[Dict[str, Any]],
        system_instruction: Optional[str] = None
    ) -> str:
        """
        Synthesizes an intelligent answer fusing both Graph Ontology facts and Vector DB semantic passages.
        """
        system_prompt = system_instruction or (
            "Bạn là trợ lý AI thông minh tích hợp trong hệ thống Groupware doanh nghiệp IQ NFFICE.\n"
            "Nhiệm vụ của bạn là trả lời câu hỏi của người dùng một cách chính xác, chuyên nghiệp và đầy đủ dựa trên:\n"
            "1. Cấu trúc tổ chức, phòng ban, phân quyền và quan hệ quản lý từ Đồ thị Tri thức (Graph Ontology).\n"
            "2. Nội dung chi tiết các thông báo, đơn đề xuất và trao đổi từ Kho văn bản/Vector DB.\n"
            "Nếu thông tin không có trong tài liệu được cung cấp, hãy trung thực trả lời chưa có dữ liệu, không tự bịa đặt."
        )

        # Format Graph Context
        if graph_facts:
            graph_context_str = "\n".join(f"- {f}" for f in graph_facts)
        else:
            graph_context_str = "Không tìm thấy quan hệ đồ thị tương ứng."

        # Format Vector Context
        if vector_passages:
            vector_context_str = "\n\n".join(
                f"[{p.get('source_type', 'Tài liệu').upper()}] {p.get('text', '')}"
                for p in vector_passages
            )
        else:
            vector_context_str = "Không tìm thấy nội dung văn bản liên quan."

        user_content = f"""Dưới đây là thông tin thực tế được trích xuất từ hệ thống:

=== DỮ LIỆU ĐỒ THỊ QUAN HỆ & CẤU TRÚC (Graph Facts) ===
{graph_context_str}

=== DỮ LIỆU TÀI LIỆU & TRAO ĐỔI (Vector Context) ===
{vector_context_str}

=== CÂU HỎI CỦA NGƯỜI DÙNG ===
{user_query}

Hãy trả lời bằng tiếng Việt rõ ràng, ngắn gọn và có cấu trúc:"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]

        return self.chat_completion(messages)
