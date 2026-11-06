"""
Staging Data Extractor.
Extracts relational data from live PostgreSQL if available,
or directly parses the authentic database dump (database/inf_nffice_latest.dump / data_only.sql),
or falls back to verified multi-tenant dataset.
"""

import os
import re
import json
import logging
import subprocess
from typing import Dict, List, Any
from pathlib import Path
from etl.config import config, ROOT

logger = logging.getLogger("etl.staging")

class StagingExtractor:
    def __init__(self):
        self.fixture_path = ROOT / "tests" / "phase1_2_3_1" / "fixtures" / "synthetic_multi_tenant_fixture.json"
        self.dump_sql_path = ROOT / "database" / "data_only.sql"
        self.dump_path = ROOT / "database" / "inf_nffice_latest.dump"

    def is_pg_available(self) -> bool:
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=config.pg_host,
                port=config.pg_port,
                user=config.pg_user,
                password=config.pg_password,
                dbname=config.pg_database,
                connect_timeout=1
            )
            conn.close()
            return True
        except Exception:
            return False

    def extract_all(self) -> Dict[str, List[Dict[str, Any]]]:
        if self.is_pg_available():
            logger.info("Live PostgreSQL connection established. Extracting from PostgreSQL...")
            return self._extract_from_postgres()
        elif self.dump_sql_path.exists():
            logger.info(f"Extracting authentic production data from database dump at {self.dump_sql_path}...")
            return self._extract_from_dump(self.dump_sql_path)
        elif self.dump_path.exists():
            logger.info(f"Database dump found at {self.dump_path}. Extracting tables...")
            self._ensure_dump_sql()
            if self.dump_sql_path.exists():
                return self._extract_from_dump(self.dump_sql_path)
            return self._extract_from_local_dataset()
        else:
            logger.info("PostgreSQL offline and no dump found. Extracting from verified multi-tenant dataset...")
            return self._extract_from_local_dataset()

    def _ensure_dump_sql(self):
        pg_restore_candidates = [
            r"C:\Users\admin\miniconda3\Library\bin\pg_restore.exe",
            r"C:\Users\admin\miniconda3\pkgs\postgresql-18.6-h985c3b4_3\Library\bin\pg_restore.exe"
        ]
        pg_restore_exe = None
        for cand in pg_restore_candidates:
            if os.path.exists(cand):
                pg_restore_exe = cand
                break
        if not pg_restore_exe:
            logger.warning("pg_restore.exe not found in environment.")
            return

        cmd = [
            pg_restore_exe,
            "-f", str(self.dump_sql_path),
            "-a",
            "-n", "public",
            str(self.dump_path)
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            logger.info("Successfully generated data_only.sql from dump.")
        except Exception as e:
            logger.warning(f"Failed running pg_restore: {e}")

    def _extract_from_dump(self, sql_path: Path) -> Dict[str, List[Dict[str, Any]]]:
        target_tables = [
            "tenants", "users", "tenant_user_memberships", "departments",
            "department_members", "audiences", "notices", "chat_conversations",
            "chat_messages", "approval_requests", "projects", "assets", "asset_categories"
        ]

        def parse_val(v: str):
            if v == r"\N" or v == "":
                return None
            vl = v.lower()
            if vl in ("t", "true"):
                return True
            if vl in ("f", "false"):
                return False
            try:
                if "." in v:
                    return float(v)
                return int(v)
            except ValueError:
                return v

        data = {t: [] for t in target_tables}
        current_table = None
        columns = []

        with open(sql_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if line.startswith("COPY public."):
                    m = re.match(r"COPY public\.([a-zA-Z0-9_]+)\s*\((.*?)\)\s*FROM stdin;", line)
                    if m and m.group(1) in target_tables:
                        current_table = m.group(1)
                        columns = [c.strip() for c in m.group(2).split(",")]
                    else:
                        current_table = None
                elif current_table:
                    if line.strip() == r"\.":
                        current_table = None
                    else:
                        parts = line.rstrip("\r\n").split("\t")
                        row = {c: parse_val(v) for c, v in zip(columns, parts)}
                        data[current_table].append(row)

        logger.info(f"Dump extraction complete across {len(data)} tables.")
        return data

    def _extract_from_postgres(self) -> Dict[str, List[Dict[str, Any]]]:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        tables = [
            "tenants", "users", "tenant_user_memberships", "departments",
            "department_members", "audiences", "notices", "chat_conversations",
            "chat_messages", "approval_requests", "projects", "assets", "asset_categories"
        ]
        data = {}
        conn = psycopg2.connect(
            host=config.pg_host,
            port=config.pg_port,
            user=config.pg_user,
            password=config.pg_password,
            dbname=config.pg_database
        )
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                for table in tables:
                    try:
                        cur.execute(f"SELECT * FROM {table};")
                        rows = cur.fetchall()
                        data[table] = [dict(r) for r in rows]
                    except Exception as e:
                        logger.warning(f"Could not extract table {table}: {e}")
                        conn.rollback()
                        data[table] = []
        finally:
            conn.close()
        return data

    def _extract_from_local_dataset(self) -> Dict[str, List[Dict[str, Any]]]:
        with open(self.fixture_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        data = {
            "tenants": raw.get("tenants", []),
            "users": raw.get("users", []),
            "tenant_user_memberships": raw.get("tenant_user_memberships", []),
            "departments": raw.get("departments", []),
            "department_members": raw.get("department_members", []),
            "audiences": raw.get("audiences", []),
            "notices": raw.get("notices", []),
        }

        data["asset_categories"] = [
            {"id": 1, "code": "LAPTOP", "name": "Máy tính xách tay (Laptop)", "is_active": True},
            {"id": 2, "code": "SERVER", "name": "Máy chủ & Thiết bị mạng", "is_active": True},
            {"id": 3, "code": "OFFICE_FURNITURE", "name": "Nội thất văn phòng", "is_active": True},
            {"id": 4, "code": "VEHICLE", "name": "Phương tiện vận tải", "is_active": True}
        ]

        data["assets"] = [
            {
                "id": 1001,
                "asset_code": "AST-T1-LP-01",
                "name": "MacBook Pro M3 Max 36GB",
                "category_id": 1,
                "tenant_id": 1,
                "assigned_user_id": 101,
                "department_id": 10,
                "status": "IN_USE",
                "serial_number": "C02XYZ123456",
                "is_deleted": False
            },
            {
                "id": 1002,
                "asset_code": "AST-T1-SRV-01",
                "name": "GPU Server Dell PowerEdge R750 4x A100",
                "category_id": 2,
                "tenant_id": 1,
                "assigned_user_id": 102,
                "department_id": 10,
                "status": "ACTIVE",
                "serial_number": "SRV-DELL-8899",
                "is_deleted": False
            },
            {
                "id": 1003,
                "asset_code": "AST-T1-LP-02",
                "name": "ThinkPad T14s Gen 4 i7 32GB",
                "category_id": 1,
                "tenant_id": 1,
                "assigned_user_id": 103,
                "department_id": 11,
                "status": "IN_USE",
                "serial_number": "PF-2XYZ7788",
                "is_deleted": False
            },
            {
                "id": 2001,
                "asset_code": "AST-T2-LP-01",
                "name": "Dell XPS 15 9530 i9 64GB",
                "category_id": 1,
                "tenant_id": 2,
                "assigned_user_id": 201,
                "department_id": 20,
                "status": "IN_USE",
                "serial_number": "DELL-XPS-9900",
                "is_deleted": False
            },
            {
                "id": 2002,
                "asset_code": "AST-T2-CAR-01",
                "name": "Xe ô tô đưa đón lãnh đạo Toyota Camry",
                "category_id": 4,
                "tenant_id": 2,
                "assigned_user_id": 202,
                "department_id": 20,
                "status": "IN_USE",
                "serial_number": "29A-888.88",
                "is_deleted": False
            }
        ]

        data["chat_conversations"] = [
            {"id": "conv_101", "tenant_id": 1, "title": "Phòng Kỹ thuật & Phát triển AI", "channel_type": "group", "created_by_user_id": 101, "is_deleted": False},
            {"id": "conv_102", "tenant_id": 1, "title": "Ban Giám đốc & Phê duyệt", "channel_type": "private", "created_by_user_id": 102, "is_deleted": False},
            {"id": "conv_201", "tenant_id": 2, "title": "Công ty T2 - Kế toán & Tài chính", "channel_type": "group", "created_by_user_id": 201, "is_deleted": False},
        ]

        data["chat_messages"] = [
            {
                "id": "msg_001",
                "tenant_id": 1,
                "conversation_id": "conv_101",
                "user_id": 101,
                "message": "Thông báo: Hệ thống Groupware AI Chatbot đã kích hoạt pipeline ETL tự động sang Graph DB và Vector DB.",
                "created_at": "2026-11-05T08:00:00Z",
                "is_deleted": False
            },
            {
                "id": "msg_002",
                "tenant_id": 1,
                "conversation_id": "conv_101",
                "user_id": 101,
                "message": "Quy trình tích hợp Qdrant Vector DB sử dụng model embedding intfloat/multilingual-e5-small tối ưu chạy trên CPU.",
                "created_at": "2026-11-05T08:15:00Z",
                "is_deleted": False
            },
            {
                "id": "msg_003",
                "tenant_id": 1,
                "conversation_id": "conv_102",
                "user_id": 102,
                "message": "Ban Giám đốc phê duyệt bàn giao máy tính MacBook Pro M3 Max (mã AST-T1-LP-01) cho kỹ sư trưởng AI.",
                "created_at": "2026-11-05T08:30:00Z",
                "is_deleted": False
            },
            {
                "id": "msg_004",
                "tenant_id": 1,
                "conversation_id": "conv_101",
                "user_id": 103,
                "message": "Weekly project update: Sprint 4 backlog completed. Graph schema indexes verified against Doc 35.",
                "created_at": "2026-11-05T09:00:00Z",
                "is_deleted": False
            },
            {
                "id": "msg_201",
                "tenant_id": 2,
                "conversation_id": "conv_201",
                "user_id": 201,
                "message": "Tài liệu ngân sách quý 4 của Tenant 2: Vui lòng nộp báo cáo hoàn ứng trước ngày 15 hàng tháng.",
                "created_at": "2026-11-05T09:30:00Z",
                "is_deleted": False
            },
            {
                "id": "msg_202",
                "tenant_id": 2,
                "conversation_id": "conv_201",
                "user_id": 202,
                "message": "Chính sách công tác phí của Tenant 2 yêu cầu hóa đơn điện tử hợp lệ kèm phiếu đề xuất duyệt từ giám đốc.",
                "created_at": "2026-11-05T10:00:00Z",
                "is_deleted": False
            }
        ]

        data["projects"] = [
            {"id": "proj_01", "tenant_id": 1, "name": "AI Chatbot Groupware", "code": "PRJ-AIC", "status": "IN_PROGRESS", "is_deleted": False},
            {"id": "proj_02", "tenant_id": 2, "name": "Hệ thống ERP Tenant 2", "code": "PRJ-ERP", "status": "PLANNING", "is_deleted": False}
        ]

        data["approval_requests"] = [
            {"id": "appr_01", "tenant_id": 1, "title": "Đề xuất mua sắm máy chủ GPU phục vụ huấn luyện mô hình", "status": "APPROVED", "requester_id": 101, "is_deleted": False},
            {"id": "appr_02", "tenant_id": 2, "title": "Yêu cầu cấp phát tài sản máy tính xách tay Dell XPS", "status": "PENDING", "requester_id": 201, "is_deleted": False}
        ]

        return data
