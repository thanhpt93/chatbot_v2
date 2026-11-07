"""
Chatbot Backend Web Server.
Fuses Neo4j Graph Ontology Knowledge + Qdrant Vector Semantic Retrieval + Qwen2.5-7B vLLM.
Pure Python standard library (no extra dependencies required).

Usage:
  python scripts/run_web_ui.py --port 8080
"""

import sys
import json
import logging
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from etl.config import config
from etl.llm_client import LLMClient
from etl.vector.retriever import MultiTenantRetriever

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("web.server")

# Load Graph Snapshot for offline graph retrieval
GRAPH_SNAPSHOT_PATH = ROOT / "data" / "graph_export" / "graph_snapshot.json"
graph_data = {"nodes": {}, "relationships": []}
if GRAPH_SNAPSHOT_PATH.exists():
    try:
        with open(GRAPH_SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
            logger.info("Graph snapshot loaded for RAG context.")
    except Exception as e:
        logger.warning(f"Could not load graph snapshot: {e}")

llm_client = LLMClient()
retriever = MultiTenantRetriever()

def extract_graph_facts(query: str, tenant_id: int) -> list:
    """Extracts relevant graph relations from graph snapshot based on keywords."""
    facts = []
    q_lower = query.lower()
    
    # 1. Organization & Departments
    if any(k in q_lower for k in ["phòng ban", "bộ phận", "department", "cơ cấu"]):
        depts = graph_data.get("nodes", {}).get("Department", [])
        facts.append(f"Doanh nghiệp có tổng cộng {len(depts)} phòng ban.")
        sample_depts = [d.get("name") or d.get("code") for d in depts[:10]]
        facts.append("Một số phòng ban tiêu biểu: " + ", ".join(sample_depts))

    # 2. Staff & Users
    if any(k in q_lower for k in ["nhân viên", "nhân sự", "user", "ai", "thành viên"]):
        users = graph_data.get("nodes", {}).get("User", [])
        facts.append(f"Hệ thống quản lý {len(users)} nhân sự trực thuộc doanh nghiệp.")

    # 3. IT Assets & Equipment
    if any(k in q_lower for k in ["tài sản", "laptop", "máy tính", "server", "thiết bị", "asset"]):
        assets = graph_data.get("nodes", {}).get("Asset", [])
        facts.append(f"Doanh nghiệp quản lý {len(assets)} tài sản thiết bị.")
        sample_assets = [a.get("name") or a.get("model") for a in assets[:5] if a.get("name")]
        if sample_assets:
            facts.append("Các thiết bị mẫu: " + " | ".join(sample_assets))

    # 4. Approvals & Requests
    if any(k in q_lower for k in ["phê duyệt", "đơn", "yêu cầu", "approval", "đề xuất"]):
        approvals = graph_data.get("nodes", {}).get("ApprovalRequest", [])
        facts.append(f"Quy trình ghi nhận {len(approvals)} đơn từ/yêu cầu phê duyệt.")

    # 5. Projects
    if any(k in q_lower for k in ["dự án", "project"]):
        projects = graph_data.get("nodes", {}).get("Project", [])
        facts.append(f"Hiện có {len(projects)} dự án đang được theo dõi.")
        sample_prj = [p.get("name") or p.get("code") for p in projects[:6] if p.get("name")]
        facts.append("Các dự án: " + ", ".join(sample_prj))

    return facts

class ChatbotHTTPHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "web"), **kwargs)

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                payload = json.loads(body)
                query = payload.get("query", "").strip()
                tenant_id = int(payload.get("tenant_id", 1))

                logger.info(f"Received query: '{query}' (tenant_id={tenant_id})")

                # Step 1: Extract Graph Facts
                graph_facts = extract_graph_facts(query, tenant_id)

                # Step 2: Semantic Vector Search
                vector_results = retriever.search(query=query, tenant_id=tenant_id, top_k=3)

                # Step 3: LLM Generation
                evidence_text = ""
                if graph_facts:
                    evidence_text += "--- GRAPH ONTOLOGY ---\n" + "\n".join(graph_facts) + "\n\n"
                if vector_results:
                    evidence_text += "--- VECTOR RETRIEVAL (Qdrant) ---\n"
                    for idx, v in enumerate(vector_results, 1):
                        evidence_text += f"{idx}. [{v.get('source_type')}] (score: {v.get('score'):.2f}): {v.get('text')}\n"

                answer = llm_client.rag_answer(
                    user_query=query,
                    graph_facts=graph_facts,
                    vector_passages=vector_results
                )

                response_data = {
                    "status": "SUCCESS",
                    "response": answer,
                    "evidence": evidence_text.strip()
                }

            except Exception as e:
                logger.error(f"Error handling /api/chat: {e}", exc_info=True)
                response_data = {
                    "status": "ERROR",
                    "error": str(e)
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_error(404, "Endpoint Not Found")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="IQ NFFICE Chatbot Web Interface")
    parser.add_argument("--port", type=int, default=8080, help="Web server port (default: 8080)")
    args = parser.parse_args()

    server_address = ("", args.port)
    httpd = HTTPServer(server_address, ChatbotHTTPHandler)
    print("=" * 65)
    print(f"      IQ NFFICE AI CHATBOT WEB INTERFACE RUNNING        ")
    print("=" * 65)
    print(f"Local URL           : http://localhost:{args.port}")
    print(f"Graph Snapshot      : {len(graph_data.get('nodes', {}))} node types loaded")
    print(f"LLM Serving Backend : {config.llm_api_base} ({config.llm_model_name})")
    print(f"Vector Database     : Qdrant Collection '{config.qdrant_collection}'")
    print("-" * 65)
    print("Press Ctrl+C to stop the web server.\n")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server...")
        httpd.server_close()

if __name__ == "__main__":
    main()
