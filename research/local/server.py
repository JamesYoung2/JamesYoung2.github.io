from flask import Flask, jsonify, request, render_template_string
import sqlite3
import re
import json
import os

app = Flask(__name__)
DB_NAME = "graph_data.db"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Z_n Graph Explorer</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {
            --bg-color: #121212;
            --card-bg: #1e1e1e;
            --text-color: #e0e0e0;
            --input-bg: #2c2c2c;
            --border-color: #333;
            --accent-color: #bb86fc;
            --btn-bg: #3700b3;
            --btn-text: #ffffff;
            --highlight: #3a3a3a;
        }

        body.light-mode {
            --bg-color: #f4f4f4;
            --card-bg: #ffffff;
            --text-color: #333333;
            --input-bg: #ffffff;
            --border-color: #ddd;
            --accent-color: #007bff;
            --btn-bg: #007bff;
            --btn-text: #ffffff;
            --highlight: #ffffcc;
        }

        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            padding: 20px; 
            background-color: var(--bg-color); 
            color: var(--text-color);
            transition: background-color 0.3s, color 0.3s;
        }

        .header-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .stats-box {
            background: var(--card-bg);
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            font-weight: bold;
            color: var(--accent-color);
        }

        .controls {
            display: flex;
            gap: 10px;
            align-items: center;
        }

        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: var(--card-bg); 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 4px 10px rgba(0,0,0,0.3); 
        }

        /* Search & Filter Bar */
        .filter-container {
            display: flex;
            flex-direction: column;
            gap: 10px;
            margin-bottom: 20px;
        }

        .filter-row {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            align-items: center;
        }

        .search-box { 
            flex-grow: 2; 
            padding: 10px; 
            font-size: 16px; 
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            border-radius: 4px;
        }
        
        .num-input {
            width: 100px;
            padding: 10px;
            font-size: 16px;
            background: var(--input-bg);
            border: 1px solid var(--border-color);
            color: var(--text-color);
            border-radius: 4px;
        }

        .checkbox-wrapper {
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 14px;
            user-select: none;
            background: var(--input-bg);
            padding: 8px 12px;
            border-radius: 4px;
            border: 1px solid var(--border-color);
        }

        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { 
            border-bottom: 1px solid var(--border-color); 
            padding: 12px 8px; 
            text-align: left; 
        }
        th { 
            background-color: var(--input-bg); 
            color: var(--accent-color); 
            position: sticky;
            top: 0;
        }
        tr:hover { background-color: var(--highlight); }

        #network { 
            width: 100%; 
            height: 500px; 
            border: 1px solid var(--border-color); 
            margin-top: 20px; 
            margin-bottom: 20px;
            display: none; 
            background: #222; 
            border-radius: 4px;
        }
        body.light-mode #network { background: #fff; }

        .btn { 
            padding: 10px 20px; 
            cursor: pointer; 
            background: var(--btn-bg); 
            color: var(--btn-text); 
            border: none; 
            border-radius: 4px; 
            font-weight: bold;
        }
        .btn-small { padding: 5px 10px; font-size: 12px; }
        .btn-toggle { background: transparent; border: 1px solid var(--border-color); color: var(--text-color); }

        .loading-trigger {
            text-align: center;
            padding: 20px;
            color: #888;
        }
    </style>
</head>
<body>

    <div class="container">
        <div class="header-bar">
            <h1>Z_n Graph Explorer</h1>
            <div class="controls">
                <div class="stats-box" id="maxNDisplay">Max N: Loading...</div>
                <button class="btn btn-toggle" onclick="toggleTheme()">Subjective Light/Dark</button>
            </div>
        </div>

        <div id="network"></div>

        <div class="filter-container">
            <div class="filter-row">
                <input type="text" id="searchInput" class="search-box" placeholder="Search Components: 6, (3, , (1,2)..." onkeyup="handleEnter(event)">
                <input type="number" id="minN" class="num-input" placeholder="Min N">
                <input type="number" id="maxN" class="num-input" placeholder="Max N">
                <button class="btn" onclick="resetAndSearch()">Search</button>
            </div>
            <div class="filter-row">
                <label class="checkbox-wrapper">
                    <input type="checkbox" id="hidePrimes" checked onchange="resetAndSearch()"> Hide Primes
                </label>
                <label class="checkbox-wrapper">
                    <input type="checkbox" id="requireComplete" onchange="resetAndSearch()"> Must have Complete Component
                </label>
            </div>
        </div>
        
        <table id="resultsTable">
            <thead>
                <tr>
                    <th width="10%">n</th>
                    <th width="60%">Components</th>
                    <th width="15%">w (Cardinality)</th>
                    <th width="15%">Action</th>
                </tr>
            </thead>
            <tbody></tbody>
        </table>
        
        <div id="loadingTrigger" class="loading-trigger">
            Scroll to load more...
        </div>
    </div>

    <script>
        let offset = 0;
        let limit = 50;
        let isLoading = false;
        let hasMore = true;
        
        document.addEventListener('DOMContentLoaded', () => {
            updateStats();
            resetAndSearch();
            
            const observer = new IntersectionObserver((entries) => {
                if(entries[0].isIntersecting && !isLoading && hasMore) {
                    performSearch(false);
                }
            }, { threshold: 0.1 });
            
            observer.observe(document.getElementById('loadingTrigger'));
        });

        function handleEnter(e) {
            if(e.key === 'Enter') resetAndSearch();
        }

        function toggleTheme() {
            document.body.classList.toggle('light-mode');
        }

        async function updateStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                document.getElementById('maxNDisplay').innerText = "Database Max N: " + data.max_n;
            } catch(e) { console.error(e); }
        }

        function resetAndSearch() {
            offset = 0;
            hasMore = true;
            document.querySelector('#resultsTable tbody').innerHTML = '';
            document.getElementById('network').style.display = 'none';
            performSearch(true);
        }

        async function performSearch(isReset) {
            if (isLoading || (!hasMore && !isReset)) return;
            isLoading = true;
            document.getElementById('loadingTrigger').innerText = "Loading...";

            const query = document.getElementById('searchInput').value;
            const minN = document.getElementById('minN').value;
            const maxN = document.getElementById('maxN').value;
            const hidePrimes = document.getElementById('hidePrimes').checked;
            const requireComplete = document.getElementById('requireComplete').checked;

            let url = `/api/search?q=${encodeURIComponent(query)}&offset=${offset}&limit=${limit}`;
            if(minN) url += `&min=${minN}`;
            if(maxN) url += `&max=${maxN}`;
            url += `&hide_primes=${hidePrimes}`;
            url += `&req_complete=${requireComplete}`;

            try {
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.results.length < limit) {
                    hasMore = false;
                    document.getElementById('loadingTrigger').innerText = "End of results";
                } else {
                    document.getElementById('loadingTrigger').innerText = "Scroll for more";
                }

                const tbody = document.querySelector('#resultsTable tbody');
                
                data.results.forEach(row => {
                    const tr = document.createElement('tr');
                    const graphBtn = row.has_graph 
                        ? `<button class="btn btn-small" onclick='drawGraph(${row.n})'>Graph</button>` 
                        : '<span style="color:gray; font-size:0.9em;">Too Large</span>';

                    tr.innerHTML = `
                        <td><strong>${row.n}</strong></td>
                        <td style="word-break: break-all;">${row.components}</td>
                        <td>${row.w}</td>
                        <td>${graphBtn}</td>
                    `;
                    tbody.appendChild(tr);
                });

                offset += limit;
            } catch (err) {
                console.error(err);
            } finally {
                isLoading = false;
            }
        }

        async function drawGraph(n) {
            const response = await fetch('/api/graph/' + n);
            const data = await response.json();
            
            const container = document.getElementById('network');
            container.style.display = 'block';

            const nodes = new vis.DataSet(data.nodes);
            const edges = new vis.DataSet(data.edges);

            const nodeMap = {}; 
            data.nodes.forEach(n => nodeMap[n.id] = n);
            
            const adj = {}; 
            data.nodes.forEach(n => adj[n.id] = []);
            data.edges.forEach(e => {
                if(!adj[e.from]) adj[e.from] = [];
                if(!adj[e.to]) adj[e.to] = [];
                adj[e.from].push(e.to);
                adj[e.to].push(e.from);
            });

            const paletteA = "#ff5722"; 
            const paletteB = "#00bcd4"; 
            const paletteC = "#ffeb3b"; 

            const groups = {};
            data.nodes.forEach(n => {
                if(!groups[n.group]) groups[n.group] = [];
                groups[n.group].push(n.id);
            });

            Object.keys(groups).forEach(gId => {
                const groupNodes = groups[gId];
                if(groupNodes.length === 0) return;

                const colors = {}; 
                let isBipartite = true;
                const visited = new Set();
                
                groupNodes.forEach(root => {
                    if(visited.has(root)) return;
                    
                    const q = [{id: root, c: 0}];
                    colors[root] = 0;
                    visited.add(root);

                    while(q.length > 0) {
                        const curr = q.shift();
                        const nextColor = 1 - curr.c;
                        const neighbors = adj[curr.id] || [];
                        for(let neighborId of neighbors) {
                            if (nodeMap[neighborId].group != gId) continue;

                            if(!visited.has(neighborId)) {
                                visited.add(neighborId);
                                colors[neighborId] = nextColor;
                                q.push({id: neighborId, c: nextColor});
                            } else {
                                if(colors[neighborId] === curr.c) isBipartite = false;
                            }
                        }
                    }
                });

                groupNodes.forEach(nid => {
                    if(!isBipartite) {
                        nodes.update({id: nid, color: {background: paletteC, border: paletteC}});
                    } else {
                        const c = colors[nid] === 0 ? paletteA : paletteB;
                        nodes.update({id: nid, color: {background: c, border: c}});
                    }
                });
            });
            
            const options = {
                nodes: {
                    shape: 'dot',
                    size: 15,
                    font: { size: 16, color: '#ffffff', strokeWidth: 2, strokeColor: '#000000' }
                },
                physics: { stabilization: false, barnesHut: { gravitationalConstant: -2000 } },
                interaction: { hover: true }
            };
            
            new vis.Network(container, {nodes, edges}, options);
            container.scrollIntoView({behavior: "smooth"});
        }
    </script>
</body>
</html>
"""

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/stats')
def stats():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT MAX(n) as max_n FROM records")
    row = cur.fetchone()
    conn.close()
    return jsonify({"max_n": row['max_n'] if row and row['max_n'] else 0})

@app.route('/api/graph/<int:n>')
def get_graph(n):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT graph_data FROM records WHERE n = ?", (n,))
    row = cur.fetchone()
    conn.close()
    if row and row['graph_data']:
        return jsonify(json.loads(row['graph_data']))
    return jsonify({})

@app.route('/api/search')
def search():
    query_str = request.args.get('q', '').strip()
    min_n = request.args.get('min', '').strip()
    max_n = request.args.get('max', '').strip()
    hide_primes = request.args.get('hide_primes', 'false') == 'true'
    req_complete = request.args.get('req_complete', 'false') == 'true'
    
    limit = request.args.get('limit', default=50, type=int)
    offset = request.args.get('offset', default=0, type=int)

    conn = get_db()
    cur = conn.cursor()

    sql_clauses = []
    params = []

    # Range Filters
    if min_n:
        sql_clauses.append("n >= ?")
        params.append(int(min_n))
    if max_n:
        sql_clauses.append("n <= ?")
        params.append(int(max_n))

    # Prime Filter
    if hide_primes:
        sql_clauses.append("is_prime = 0")

    # Complete Component Filter (Any C_m)
    if req_complete:
        sql_clauses.append("components_str LIKE '%C_{%'")

    # Text Filters
    if query_str:
        parts = [p.strip() for p in query_str.split('),')] 
        comp_clauses = []
        
        for part in parts:
            part = part.replace(')', '').strip()
            
            # Exact Complete Component: "6" -> C_{6}
            if re.match(r'^\d+$', part):
                comp_clauses.append(f"components_str LIKE ?")
                params.append(f"%C_{{{part}}}%")
            
            # Partial K: "(6,"
            elif '(' in part and ',' in part and (part.endswith(',') or part.startswith(',')):
                nums = re.findall(r'\d+', part)
                if nums:
                    val = nums[0]
                    sub_sql = "(components_str LIKE ? OR components_str LIKE ?)"
                    comp_clauses.append(sub_sql)
                    params.append(f"%K_{{{val},%")
                    params.append(f"%,{val}}}%")

            # Full K: "(3,4)"
            elif '(' in part and ',' in part:
                nums = re.findall(r'\d+', part)
                if len(nums) >= 2:
                    n1, n2 = int(nums[0]), int(nums[1])
                    low, high = sorted([n1, n2])
                    comp_clauses.append("components_str LIKE ?")
                    params.append(f"%K_{{{low},{high}}}%")
        
        if comp_clauses:
            sql_clauses.append(" AND ".join(comp_clauses))

    where_clause = " AND ".join(sql_clauses) if sql_clauses else "1=1"
    
    sql = f"""
        SELECT n, components_str, w, graph_data 
        FROM records 
        WHERE {where_clause} 
        ORDER BY n ASC 
        LIMIT ? OFFSET ?
    """
    params.append(limit)
    params.append(offset)
    
    cur.execute(sql, params)
    results = cur.fetchall()
    conn.close()

    rows = []
    for r in results:
        rows.append({
            "n": r['n'],
            "components": r['components_str'],
            "w": r['w'],
            "has_graph": r['graph_data'] != 'null' and r['graph_data'] is not None
        })

    return jsonify({"results": rows})

if __name__ == "__main__":
    if not os.path.exists(DB_NAME):
        print("Database not found. Please run generator.py first.")
    app.run(port=47274, debug=True, use_reloader=False, threaded=True)
