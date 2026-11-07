"""
Graph Transformer Module.
Transforms staging relational tables into Architecture B Graph Nodes and Relationships.
Enforces:
- 24 approved Node types & 43 Relationship types (Docs 30, 31)
- NM-02 (:User) enriched with :user_profiles (display_name, position, grade, mobile_phone)
- NM-16 (:Asset), NM-17 (:AssetCategory)
- RM-30 (:Asset)-[:ASSIGNED_TO]->(:User)
- RM-31 (:Asset)-[:LOCATED_IN]->(:Department)
- RM-32 (:Asset)-[:CATEGORIZED_AS]->(:AssetCategory)
- ChatMessage Option A: NEVER create ChatMessage nodes in Neo4j!
- Multi-Tenant isolation & property projection
- Tombstone soft-delete semantics (is_deleted: true)
- 100% referential integrity across all relationships
"""

from typing import Dict, List, Any

class GraphTransformer:
    def transform(self, staging_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        nodes = {
            "Tenant": [],
            "User": [],
            "Department": [],
            "ChatConversation": [],
            "Notice": [],
            "Audience": [],
            "Project": [],
            "ApprovalRequest": [],
            "AssetCategory": [],
            "Asset": []
        }
        relationships = []

        # 1. Transform Tenants (NM-01)
        for t in staging_data.get("tenants", []):
            t_id = t["id"]
            nodes["Tenant"].append({
                "id": t_id,
                "name": t.get("name") or t.get("tenant_key") or f"Tenant {t_id}",
                "domain": t.get("domain", ""),
                "is_active": t.get("is_active", True) if t.get("status") is None else (t.get("status") == "active"),
                "is_deleted": t.get("is_deleted", False)
            })

        # 2. Transform Users (NM-02) & Tenant Memberships + Profile Enrichment
        user_tenants = {}
        for m in staging_data.get("tenant_user_memberships", []):
            user_tenants[m["user_id"]] = m.get("tenant_id", 1)

        # Index user_profiles by user_id
        profiles_by_user = {}
        for p in staging_data.get("user_profiles", []):
            uid = p.get("user_id")
            if uid is not None:
                profiles_by_user[int(uid)] = p

        for u in staging_data.get("users", []):
            u_id = u["id"]
            t_id = user_tenants.get(u_id, u.get("tenant_id", 1))
            prof = profiles_by_user.get(u_id, {})
            
            # Enrich with official display_name from user_profiles
            display_name = prof.get("display_name") or u.get("username", f"user_{u_id}")
            position = prof.get("position") or prof.get("duty") or ""
            grade = prof.get("grade") or ""
            mobile_phone = prof.get("mobile_phone") or ""

            nodes["User"].append({
                "id": u_id,
                "tenant_id": t_id,
                "username": u.get("username", f"user_{u_id}"),
                "display_name": display_name,
                "email": u.get("email", ""),
                "position": position,
                "grade": grade,
                "mobile_phone": mobile_phone,
                "status": "ACTIVE" if u.get("is_active", True) else "INACTIVE",
                "is_deleted": u.get("is_deleted", False)
            })
            relationships.append({
                "source_label": "User", "source_id": u_id,
                "rel_type": "BELONGS_TO",
                "target_label": "Tenant", "target_id": t_id,
                "tenant_id": t_id
            })

        # 3. Transform Departments (NM-03), Hierarchy & Members
        for d in staging_data.get("departments", []):
            d_id = d["id"]
            t_id = d.get("tenant_id", 1)
            dept_name = d.get("name") or d.get("code") or f"Dept {d_id}"
            nodes["Department"].append({
                "id": d_id,
                "tenant_id": t_id,
                "name": dept_name,
                "code": d.get("code", ""),
                "is_deleted": d.get("is_deleted", False)
            })
            relationships.append({
                "source_label": "Department", "source_id": d_id,
                "rel_type": "BELONGS_TO",
                "target_label": "Tenant", "target_id": t_id,
                "tenant_id": t_id
            })
            # RM-05: Department Hierarchy (SUB_DEPARTMENT_OF)
            if d.get("parent_id") is not None:
                relationships.append({
                    "source_label": "Department", "source_id": d_id,
                    "rel_type": "SUB_DEPARTMENT_OF",
                    "target_label": "Department", "target_id": d["parent_id"],
                    "tenant_id": t_id
                })
            # RM-04: Department Manager (MANAGES)
            if d.get("manager_user_id") is not None:
                relationships.append({
                    "source_label": "User", "source_id": d["manager_user_id"],
                    "rel_type": "MANAGES",
                    "target_label": "Department", "target_id": d_id,
                    "tenant_id": t_id
                })

        # RM-03: Department Membership
        for dm in staging_data.get("department_members", []):
            u_id = dm["user_id"]
            dept_id = dm["department_id"]
            t_id = dm.get("tenant_id") or user_tenants.get(u_id, 1)
            relationships.append({
                "source_label": "User", "source_id": u_id,
                "rel_type": "MEMBER_OF",
                "target_label": "Department", "target_id": dept_id,
                "tenant_id": t_id
            })

        # 4. Transform Audiences (NM-20)
        for a in staging_data.get("audiences", []):
            a_id = a["id"]
            t_id = a.get("tenant_id") or user_tenants.get(a.get("owner_user_id"))
            is_sys = a.get("is_system", a.get("tenant_id") is None)
            nodes["Audience"].append({
                "id": a_id,
                "tenant_id": t_id if t_id else 1,
                "name": a.get("name") or f"Audience {a_id}",
                "is_system": bool(is_sys),
                "is_deleted": a.get("is_deleted", False)
            })

        # 5. Transform Notices (NM-09) & RM-20, RM-21
        for n in staging_data.get("notices", []):
            n_id = n["id"]
            author_id = n.get("created_by_user_id")
            t_id = n.get("tenant_id") or (user_tenants.get(author_id, 1) if author_id else 1)
            nodes["Notice"].append({
                "id": n_id,
                "tenant_id": t_id,
                "title": n.get("title") or f"Notice {n_id}",
                "notice_type": n.get("notice_type", "general"),
                "priority": n.get("priority", "normal"),
                "is_published": n.get("is_published", True) if n.get("published_at") else False,
                "is_deleted": n.get("is_deleted", False)
            })
            if author_id:
                relationships.append({
                    "source_label": "Notice", "source_id": n_id,
                    "rel_type": "CREATED_BY",
                    "target_label": "User", "target_id": author_id,
                    "tenant_id": t_id
                })
            if "audience_id" in n and n["audience_id"] is not None:
                relationships.append({
                    "source_label": "Notice", "source_id": n_id,
                    "rel_type": "TARGETS",
                    "target_label": "Audience", "target_id": n["audience_id"],
                    "tenant_id": t_id
                })

        # 6. Transform Chat Conversations (NM-08) & Conversation Members
        for c in staging_data.get("chat_conversations", []):
            c_id = c["id"]
            t_id = c.get("tenant_id", 1)
            nodes["ChatConversation"].append({
                "id": c_id,
                "tenant_id": t_id,
                "title": c.get("title") or f"Conversation {c_id}",
                "conversation_type": c.get("conversation_type", "direct"),
                "is_deleted": c.get("is_deleted", False)
            })
            relationships.append({
                "source_label": "ChatConversation", "source_id": c_id,
                "rel_type": "BELONGS_TO",
                "target_label": "Tenant", "target_id": t_id,
                "tenant_id": t_id
            })

        for m in staging_data.get("chat_conversation_members", []):
            c_id = m.get("conversation_id")
            u_id = m.get("user_id")
            t_id = m.get("tenant_id") or user_tenants.get(u_id, 1)
            if c_id and u_id:
                relationships.append({
                    "source_label": "User", "source_id": u_id,
                    "rel_type": "PARTICIPATES_IN",
                    "target_label": "ChatConversation", "target_id": c_id,
                    "tenant_id": t_id
                })

        # 7. Transform Projects (NM-06) & Approval Requests (NM-10)
        for p in staging_data.get("projects", []):
            p_id = p["id"]
            t_id = p.get("tenant_id", 1)
            nodes["Project"].append({
                "id": p_id,
                "tenant_id": t_id,
                "name": p.get("name") or f"Project {p_id}",
                "code": p.get("code", ""),
                "status": p.get("status", "ACTIVE"),
                "is_deleted": p.get("is_deleted", False)
            })
            relationships.append({
                "source_label": "Project", "source_id": p_id,
                "rel_type": "BELONGS_TO",
                "target_label": "Tenant", "target_id": t_id,
                "tenant_id": t_id
            })

        for app in staging_data.get("approval_requests", []):
            app_id = app["id"]
            requester_id = app.get("requester_id") or app.get("created_by_user_id")
            t_id = app.get("tenant_id") or (user_tenants.get(requester_id, 1) if requester_id else 1)
            nodes["ApprovalRequest"].append({
                "id": app_id,
                "tenant_id": t_id,
                "title": app.get("title") or f"Approval {app_id}",
                "status": app.get("status", "PENDING"),
                "is_deleted": app.get("is_deleted", False)
            })
            if requester_id:
                relationships.append({
                    "source_label": "ApprovalRequest", "source_id": app_id,
                    "rel_type": "REQUESTED_BY",
                    "target_label": "User", "target_id": requester_id,
                    "tenant_id": t_id
                })

        # 8. Transform Asset Categories (NM-17)
        for ac in staging_data.get("asset_categories", []):
            ac_id = ac["id"]
            nodes["AssetCategory"].append({
                "id": ac_id,
                "code": ac.get("code", f"CAT_{ac_id}"),
                "name": ac.get("name") or ac.get("code", ""),
                "is_active": ac.get("is_active", True)
            })

        # 9. Transform Assets (NM-16) & Asset Relationships (RM-30, RM-31, RM-32)
        for a in staging_data.get("assets", []):
            a_id = a["id"]
            t_id = a.get("tenant_id", 1)
            asset_code = a.get("asset_code") or a.get("code") or f"AST_{a_id}"
            nodes["Asset"].append({
                "id": a_id,
                "tenant_id": t_id,
                "asset_code": asset_code,
                "name": a.get("name") or asset_code,
                "status": a.get("status", "IN_USE"),
                "serial_number": a.get("serial_number", ""),
                "is_deleted": a.get("is_deleted", False)
            })
            # Asset -> Tenant
            relationships.append({
                "source_label": "Asset", "source_id": a_id,
                "rel_type": "BELONGS_TO",
                "target_label": "Tenant", "target_id": t_id,
                "tenant_id": t_id
            })
            # RM-32: Asset -> AssetCategory
            if "category_id" in a and a["category_id"] is not None:
                relationships.append({
                    "source_label": "Asset", "source_id": a_id,
                    "rel_type": "CATEGORIZED_AS",
                    "target_label": "AssetCategory", "target_id": a["category_id"],
                    "tenant_id": t_id
                })
            # RM-30: Asset -> User (Assigned to)
            if "assigned_user_id" in a and a["assigned_user_id"] is not None:
                relationships.append({
                    "source_label": "Asset", "source_id": a_id,
                    "rel_type": "ASSIGNED_TO",
                    "target_label": "User", "target_id": a["assigned_user_id"],
                    "tenant_id": t_id
                })
            # RM-31: Asset -> Department (Located in)
            if "department_id" in a and a["department_id"] is not None:
                relationships.append({
                    "source_label": "Asset", "source_id": a_id,
                    "rel_type": "LOCATED_IN",
                    "target_label": "Department", "target_id": a["department_id"],
                    "tenant_id": t_id
                })

        # Referential integrity check: Only keep relationships whose source and target exist
        valid_nodes = set()
        for label, items in nodes.items():
            for it in items:
                valid_nodes.add((label, it["id"]))

        filtered_relationships = []
        for r in relationships:
            s = (r["source_label"], r["source_id"])
            t = (r["target_label"], r["target_id"])
            if s in valid_nodes and t in valid_nodes:
                filtered_relationships.append(r)

        return {
            "nodes": nodes,
            "relationships": filtered_relationships
        }
