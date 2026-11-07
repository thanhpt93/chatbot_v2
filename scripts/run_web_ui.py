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

# Build in-memory lookup indexes for fast graph traversal
nodes = graph_data.get("nodes", {})
relationships = graph_data.get("relationships", [])

users_by_id = {u["id"]: u for u in nodes.get("User", []) if "id" in u}
depts_by_id = {d["id"]: d for d in nodes.get("Department", []) if "id" in d}
assets_by_id = {a["id"]: a for a in nodes.get("Asset", []) if "id" in a}
projects_by_id = {p["id"]: p for p in nodes.get("Project", []) if "id" in p}
categories_by_id = {c["id"]: c for c in nodes.get("AssetCategory", []) if "id" in c}

user_depts = {}       # user_id -> list of dept
dept_members = {}     # dept_id -> list of user
dept_managers = {}    # dept_id -> user
user_assets = {}      # user_id -> list of asset
asset_users = {}      # asset_id -> user
asset_depts = {}      # asset_id -> dept
user_projects = {}    # user_id -> list of project
project_users = {}    # project_id -> list of user

for r in relationships:
    rel = r.get("rel_type")
    s_label = r.get("source_label")
    s_id = r.get("source_id")
    t_label = r.get("target_label")
    t_id = r.get("target_id")

    if rel == "MEMBER_OF" and s_label == "User" and t_label == "Department":
        dept = depts_by_id.get(t_id)
        usr = users_by_id.get(s_id)
        if dept and usr:
            user_depts.setdefault(s_id, []).append(dept)
            dept_members.setdefault(t_id, []).append(usr)
    elif rel == "MANAGES" and s_label == "User" and t_label == "Department":
        usr = users_by_id.get(s_id)
        if usr:
            dept_managers[t_id] = usr
    elif rel == "ASSIGNED_TO" and s_label == "Asset" and t_label == "User":
        usr = users_by_id.get(t_id)
        ast = assets_by_id.get(s_id)
        if usr and ast:
            user_assets.setdefault(t_id, []).append(ast)
            asset_users[s_id] = usr
    elif rel == "LOCATED_IN" and s_label == "Asset" and t_label == "Department":
        dept = depts_by_id.get(t_id)
        if dept:
            asset_depts[s_id] = dept
    elif rel == "PARTICIPATES_IN" and s_label == "User" and t_label == "Project":
        prj = projects_by_id.get(t_id)
        usr = users_by_id.get(s_id)
        if prj and usr:
            user_projects.setdefault(s_id, []).append(prj)
            project_users.setdefault(t_id, []).append(usr)

llm_client = LLMClient()
retriever = MultiTenantRetriever()

def extract_graph_facts(query: str, tenant_id: int) -> list:
    """Extracts relevant graph relations from graph snapshot based on semantic entity matching."""
    facts = []
    q_lower = query.lower()
    
    # 1. Direct Entity Matching: Users (by email, username, prefix)
    matched_users = []
    for u in nodes.get("User", []):
        email = str(u.get("email") or "").lower()
        username = str(u.get("username") or "").lower()
        email_prefix = email.split("@")[0] if "@" in email else ""
        if (email and email in q_lower) or (username and username in q_lower) or (len(email_prefix) >= 4 and email_prefix in q_lower):
            matched_users.append(u)
    
    for u in matched_users[:3]:
        u_info = f"Nhân viên {u.get('username')} (Email: {u.get('email')}, Trạng thái: {u.get('status')})"
        depts = user_depts.get(u["id"], [])
        if depts:
            dept_str = ", ".join([str(d.get("name") or d.get("code")) for d in depts])
            u_info += f" thuộc phòng ban: {dept_str}."
        else:
            u_info += "."
        
        assigned = user_assets.get(u["id"], [])
        if assigned:
            ast_str = "; ".join([f"{a.get('name') or a.get('model')} (Mã: {a.get('code')}, Serial: {a.get('serial_number')})" for a in assigned[:5]])
            u_info += f" Đang được bàn giao tài sản/thiết bị: {ast_str}."
        
        prjs = user_projects.get(u["id"], [])
        if prjs:
            prj_str = ", ".join([str(p.get("name") or p.get("code")) for p in prjs[:3]])
            u_info += f" Tham gia dự án: {prj_str}."
        
        facts.append(u_info)

    # 2. Direct Entity Matching: Departments
    matched_depts = []
    for d in nodes.get("Department", []):
        d_name = str(d.get("name") or "").lower()
        d_code = str(d.get("code") or "").lower()
        if (d_name and len(d_name) >= 3 and d_name in q_lower) or (d_code and len(d_code) >= 2 and d_code in q_lower):
            matched_depts.append(d)
    
    for d in matched_depts[:3]:
        d_info = f"Phòng ban/bộ phận '{d.get('name')}' (Mã: {d.get('code')})"
        mgr = dept_managers.get(d["id"])
        if mgr:
            d_info += f" - Trưởng phòng/Quản lý: {mgr.get('username')} ({mgr.get('email')})."
        members = dept_members.get(d["id"], [])
        if members:
            sample_m = [f"{m.get('username')} ({m.get('email')})" for m in members[:10]]
            d_info += f" Có tổng cộng {len(members)} thành viên. Danh sách thành viên mẫu: {', '.join(sample_m)}."
        facts.append(d_info)

    # 3. Direct Entity Matching: Assets
    matched_assets = []
    for a in nodes.get("Asset", []):
        a_name = str(a.get("name") or "").lower()
        a_model = str(a.get("model") or "").lower()
        a_code = str(a.get("code") or "").lower()
        a_serial = str(a.get("serial_number") or "").lower()
        if (a_code and len(a_code) >= 3 and a_code in q_lower) or (a_serial and len(a_serial) >= 4 and a_serial in q_lower):
            matched_assets.append(a)
        elif any(k in q_lower for k in ["laptop", "máy tính", "macbook", "lenovo", "dell", "thinkpad"]) and any(k in a_name or k in a_model for k in ["macbook", "lenovo", "dell", "thinkpad"]):
            for vendor in ["macbook", "lenovo", "dell", "thinkpad"]:
                if vendor in q_lower and (vendor in a_name or vendor in a_model):
                    matched_assets.append(a)
                    break
    
    for a in matched_assets[:5]:
        ast_info = f"Tài sản thiết bị: {a.get('name') or a.get('model')} (Mã: {a.get('code')}, Serial: {a.get('serial_number')}, Trạng thái: {a.get('status')})"
        holder = asset_users.get(a["id"])
        if holder:
            ast_info += f" - Người được cấp/sử dụng: {holder.get('username')} ({holder.get('email')})."
        d_loc = asset_depts.get(a["id"])
        if d_loc:
            ast_info += f" Vị trí: Phòng {d_loc.get('name')}."
        facts.append(ast_info)

    # 4. General Organization Hierarchy
    if any(k in q_lower for k in ["phòng ban", "bộ phận", "cơ cấu"]):
        depts = nodes.get("Department", [])
        facts.append(f"Doanh nghiệp có tổng cộng {len(depts)} phòng ban/bộ phận.")
        if not matched_depts:
            sample_depts = [str(d.get("name") or d.get("code")) for d in depts[:10]]
            facts.append("Một số phòng ban tiêu biểu: " + ", ".join(sample_depts))

    if any(k in q_lower for k in ["tổng quan", "cơ cấu", "toàn bộ", "hệ thống có", "doanh nghiệp có"]):
        facts.append(f"Quy mô hệ thống: {len(nodes.get('Tenant', []))} tenant, {len(nodes.get('Department', []))} phòng ban, {len(nodes.get('User', []))} nhân viên, {len(nodes.get('Asset', []))} tài sản thiết bị, {len(nodes.get('Project', []))} dự án.")

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
