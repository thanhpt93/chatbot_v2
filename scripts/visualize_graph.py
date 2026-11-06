import json
from pathlib import Path

def generate_html():
    root = Path(__file__).resolve().parent.parent
    snapshot_path = root / "data" / "graph_export" / "graph_snapshot.json"
    out_html = root / "data" / "graph_export" / "visualize_graph.html"

    if not snapshot_path.exists():
        print(f"Error: Snapshot file not found at {snapshot_path}")
        return

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    color_map = {
        "Tenant": "#FF7675",
        "User": "#74B9FF",
        "Department": "#55EFC4",
        "Notice": "#FDCB6E",
        "Audience": "#A29BFE",
        "Project": "#00CEC9",
        "ApprovalRequest": "#FD79A8",
        "AssetCategory": "#E17055",
        "Asset": "#FFEAA7",
        "ChatConversation": "#B2BEC3"
    }

    nodes_list = []
    node_id_set = set()
    label_counts = {}

    for label, items in data.get("nodes", {}).items():
        label_counts[label] = len(items)
        for item in items:
            node_id = f"{label}_{item['id']}"
            node_id_set.add(node_id)
            raw_title = item.get("name") or item.get("username") or item.get("title") or item.get("code") or f"{label} #{item['id']}"
            title_str = str(raw_title)
            nodes_list.append({
                "id": node_id,
                "label": f"{label}\n{title_str[:25]}",
                "group": label,
                "color": color_map.get(label, "#95A5A6"),
                "properties": item,
                "entityType": label,
                "name": title_str
            })

    edges_list = []
    for idx, rel in enumerate(data.get("relationships", [])):
        s = f"{rel['source_label']}_{rel['source_id']}"
        t = f"{rel['target_label']}_{rel['target_id']}"
        if s in node_id_set and t in node_id_set:
            edges_list.append({
                "id": f"e_{idx}",
                "from": s,
                "to": t,
                "label": rel.get("rel_type", ""),
                "arrows": "to",
                "color": {"color": "#b2bec3", "highlight": "#0984e3"},
                "font": {"size": 9, "align": "middle", "color": "#2d3436", "background": "#ffffffcc"}
            })

    total_nodes = len(nodes_list)
    total_edges = len(edges_list)

    raw_nodes_json = json.dumps(nodes_list, ensure_ascii=False)
    raw_edges_json = json.dumps(edges_list, ensure_ascii=False)
    color_map_json = json.dumps(color_map, ensure_ascii=False)
    label_counts_json = json.dumps(label_counts, ensure_ascii=False)

    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Groupware Authentic Neo4j Graph Visualizer</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            height: 100vh;
            background: #f8f9fa;
            color: #2d3436;
        }}
        #sidebar {{
            width: 360px;
            background: #ffffff;
            border-right: 1px solid #dfe6e9;
            box-shadow: 2px 0 8px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            z-index: 10;
        }}
        #header {{
            padding: 16px 20px;
            background: #2d3436;
            color: #fff;
        }}
        #header h2 {{
            margin: 0 0 6px 0;
            font-size: 17px;
            font-weight: 600;
        }}
        #header p {{
            margin: 0;
            font-size: 12px;
            color: #00cec9;
            font-weight: 500;
        }}
        #controls {{
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
        }}
        #controls label {{
            font-size: 12px;
            font-weight: 600;
            display: block;
            margin-bottom: 4px;
        }}
        #controls input, #controls select {{
            width: 100%;
            padding: 8px 10px;
            border: 1px solid #ccc;
            border-radius: 6px;
            margin-bottom: 10px;
            box-sizing: border-box;
            font-size: 13px;
        }}
        .btn-group {{
            display: flex;
            gap: 6px;
        }}
        .btn {{
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 600;
            font-size: 12px;
        }}
        .btn-primary {{
            background: #0984e3;
            color: #fff;
        }}
        .btn-secondary {{
            background: #dfe6e9;
            color: #2d3436;
        }}
        #details {{
            flex: 1;
            padding: 15px 20px;
            overflow-y: auto;
            font-size: 13px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
            color: #fff;
            margin-bottom: 8px;
        }}
        .prop-row {{
            margin-bottom: 6px;
            line-height: 1.4;
            word-break: break-all;
        }}
        .prop-key {{
            font-weight: 600;
            color: #636e72;
        }}
        #network-container {{
            flex: 1;
            position: relative;
            background: radial-gradient(#dcdde1 1px, transparent 1px);
            background-size: 20px 20px;
        }}
        #network {{
            width: 100%;
            height: 100%;
        }}
        #stats-bar {{
            position: absolute;
            top: 15px;
            right: 20px;
            background: rgba(255,255,255,0.95);
            padding: 8px 14px;
            border-radius: 6px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            font-size: 12px;
            font-weight: 600;
            border: 1px solid #eee;
        }}
        #legend {{
            position: absolute;
            bottom: 20px;
            right: 20px;
            background: rgba(255,255,255,0.95);
            padding: 12px 16px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            font-size: 12px;
            max-width: 260px;
            border: 1px solid #eee;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
    </style>
</head>
<body>
    <div id="sidebar">
        <div id="header">
            <h2>Groupware Graph Visualizer</h2>
            <p>Database Dump inf_nffice_latest • {total_nodes} Nodes • {total_edges} Edges</p>
        </div>
        <div id="controls">
            <label>Filter by Entity Type:</label>
            <select id="filterType" onchange="filterGraph()">
                <option value="CORE">Core Structure (Tenant + Dept + User + Project)</option>
                <option value="ALL">Show All Entities ({total_nodes})</option>
            </select>
            <label>Search Entity (Name, Email, Code):</label>
            <input type="text" id="searchInput" placeholder="e.g. hoant, ETS Team, Laptop..." onkeyup="searchNode()">
            <div class="btn-group">
                <button class="btn btn-primary" onclick="resetView()">Center View</button>
                <button id="togglePhysicsBtn" class="btn btn-secondary" onclick="togglePhysics()">Freeze Physics</button>
            </div>
        </div>
        <div id="details">
            <h3 style="margin-top:0; color:#636e72; font-size:14px;">Selected Node Details</h3>
            <p id="noSelection" style="color:#b2bec3;">Click on any node in the graph to view authentic database attributes, tenant ownership, and properties.</p>
            <div id="nodeProps" style="display:none;"></div>
        </div>
    </div>
    <div id="network-container">
        <div id="network"></div>
        <div id="stats-bar">
            Displaying: <span id="visibleStats">{total_nodes} nodes</span>
        </div>
        <div id="legend">
            <b style="display:block; margin-bottom:8px;">Database Entity Counts</b>
            <div id="legendList"></div>
        </div>
    </div>

    <script type="text/javascript">
        const rawNodes = {raw_nodes_json};
        const rawEdges = {raw_edges_json};
        const colorMap = {color_map_json};
        const labelCounts = {label_counts_json};

        const filterSelect = document.getElementById('filterType');
        const legendList = document.getElementById('legendList');

        Object.keys(colorMap).forEach(t => {{
            const cnt = labelCounts[t] || 0;
            const opt = document.createElement('option');
            opt.value = t;
            opt.innerText = t + ' (' + cnt + ')';
            filterSelect.appendChild(opt);

            const item = document.createElement('div');
            item.className = 'legend-item';
            item.innerHTML = '<div class="legend-color" style="background:' + colorMap[t] + ';"></div><span>' + t + ' (' + cnt + ')</span>';
            legendList.appendChild(item);
        }});

        // Default to Core structure (Tenant, Dept, Project, User) for smooth high-performance render
        const coreLabels = new Set(['Tenant', 'Department', 'Project', 'AssetCategory']);
        const initialNodes = rawNodes.filter(n => coreLabels.has(n.entityType));
        const initialNodeIds = new Set(initialNodes.map(n => n.id));
        const initialEdges = rawEdges.filter(e => initialNodeIds.has(e.from) && initialNodeIds.has(e.to));

        const container = document.getElementById('network');
        const nodesDataSet = new vis.DataSet(initialNodes);
        const edgesDataSet = new vis.DataSet(initialEdges);

        document.getElementById('visibleStats').innerText = initialNodes.length + ' nodes, ' + initialEdges.length + ' edges';

        const data = {{ nodes: nodesDataSet, edges: edgesDataSet }};
        let physicsEnabled = true;

        const options = {{
            nodes: {{
                shape: 'dot',
                size: 16,
                font: {{ size: 11, face: 'Segoe UI', color: '#2d3436' }},
                borderWidth: 2,
                shadow: true
            }},
            edges: {{
                width: 1.2,
                smooth: {{ type: 'continuous' }},
                arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }}
            }},
            physics: {{
                enabled: true,
                solver: 'barnesHut',
                barnesHut: {{
                    gravitationalConstant: -3500,
                    centralGravity: 0.3,
                    springLength: 90,
                    springConstant: 0.04,
                    damping: 0.8
                }},
                stabilization: {{ iterations: 40 }}
            }},
            interaction: {{ hover: true, tooltipDelay: 100 }}
        }};

        const network = new vis.Network(container, data, options);

        network.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                const nodeId = params.nodes[0];
                const node = rawNodes.find(n => n.id === nodeId);
                if (node) {{
                    showDetails(node);
                }}
            }}
        }});

        function showDetails(node) {{
            document.getElementById('noSelection').style.display = 'none';
            const propsDiv = document.getElementById('nodeProps');
            propsDiv.style.display = 'block';

            let html = '<div class="badge" style="background:' + node.color + ';">' + node.entityType + '</div>';
            html += '<h4 style="margin: 0 0 10px 0;">' + node.name + '</h4>';

            for (const [k, v] of Object.entries(node.properties)) {{
                html += '<div class="prop-row"><span class="prop-key">' + k + ':</span> <span>' + (v === null ? '<i style="color:#aaa;">null</i>' : v) + '</span></div>';
            }}
            propsDiv.innerHTML = html;
        }}

        function filterGraph() {{
            const val = document.getElementById('filterType').value;
            let filteredNodes = [];

            if (val === 'ALL') {{
                filteredNodes = rawNodes;
            }} else if (val === 'CORE') {{
                filteredNodes = rawNodes.filter(n => coreLabels.has(n.entityType));
            }} else {{
                filteredNodes = rawNodes.filter(n => n.entityType === val);
            }}

            const visibleIds = new Set(filteredNodes.map(n => n.id));
            const filteredEdges = rawEdges.filter(e => visibleIds.has(e.from) && visibleIds.has(e.to));

            nodesDataSet.clear();
            edgesDataSet.clear();
            nodesDataSet.add(filteredNodes);
            edgesDataSet.add(filteredEdges);

            document.getElementById('visibleStats').innerText = filteredNodes.length + ' nodes, ' + filteredEdges.length + ' edges';
            network.fit({{ animation: true }});
        }}

        function searchNode() {{
            const q = document.getElementById('searchInput').value.trim().toLowerCase();
            if (!q) return;

            const match = rawNodes.find(n => 
                (n.name && n.name.toLowerCase().includes(q)) || 
                (n.properties.email && String(n.properties.email).toLowerCase().includes(q)) ||
                (n.properties.code && String(n.properties.code).toLowerCase().includes(q))
            );

            if (match) {{
                if (!nodesDataSet.get(match.id)) {{
                    nodesDataSet.add(match);
                }}
                network.focus(match.id, {{ scale: 1.5, animation: true }});
                network.selectNodes([match.id]);
                showDetails(match);
            }}
        }}

        function togglePhysics() {{
            physicsEnabled = !physicsEnabled;
            network.setOptions({{ physics: {{ enabled: physicsEnabled }} }});
            document.getElementById('togglePhysicsBtn').innerText = physicsEnabled ? 'Freeze Physics' : 'Unfreeze Physics';
        }}

        function resetView() {{
            network.fit({{ animation: true }});
        }}
    </script>
</body>
</html>"""

    with open(out_html, "w", encoding="utf-8") as f:
        f.write(html_template)

    print(f"Interactive visualizer successfully updated at:\n{out_html}")

if __name__ == "__main__":
    generate_html()
