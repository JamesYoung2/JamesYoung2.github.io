import sqlite3
import math
import json
import signal
import sys
import os

DB_NAME = "graph_data.db"
running = True

# Configuration
GRAPH_THRESHOLD = 500  # Only store full node/edge data for n < this
BATCH_SIZE = 100

def signal_handler(sig, frame):
    global running
    print("\nStopping generator... finishing current batch.")
    running = False

signal.signal(signal.SIGINT, signal_handler)

def get_factors(n):
    factors = []
    for i in range(2, int(math.isqrt(n)) + 1):
        if n % i == 0:
            factors.append(i)
            if i*i != n:
                factors.append(n // i)
    factors.sort(reverse=True)
    return factors

def is_prime(n):
    if n <= 1: return False
    if n <= 3: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0: return False
        i += 6
    return True

def generate_data():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Create table
    c.execute('''CREATE TABLE IF NOT EXISTS records (
                    n INTEGER PRIMARY KEY,
                    components_str TEXT,
                    w INTEGER,
                    graph_data JSON,
                    is_prime INTEGER
                )''')
    # Create index for faster searching
    c.execute('CREATE INDEX IF NOT EXISTS idx_prime ON records (is_prime)')
    conn.commit()

    c.execute("SELECT MAX(n) FROM records")
    row = c.fetchone()
    start_n = (row[0] + 1) if row[0] is not None else 4
    
    print(f"Starting generation from n = {start_n}. Press Ctrl+C to stop.")

    curr_n = start_n
    
    while running:
        for _ in range(BATCH_SIZE): 
            if not running: break
            
            if is_prime(curr_n):
                c.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?)", 
                          (curr_n, "", 0, json.dumps(None), 1))
                curr_n += 1
                continue

            factors = get_factors(curr_n)
            factor_sets = {}
            seen_multiples = set()
            
            for f in factors:
                multiples = []
                for m in range(f, curr_n, f):
                    if m not in seen_multiples:
                        multiples.append(m)
                        seen_multiples.add(m)
                factor_sets[f] = multiples

            components = [] 
            w = 0
            processed_pairs = set()
            graph_nodes = []
            graph_edges = []
            group_id = 0

            for a in factors:
                b = curr_n // a
                if b in factors: 
                    if a < b: continue
                    
                    pair_sig = (a, b)
                    if pair_sig in processed_pairs: continue
                    processed_pairs.add(pair_sig)

                    set_a = factor_sets[a]
                    len_a = len(set_a)
                    
                    # Graphing Logic
                    if curr_n < GRAPH_THRESHOLD:
                        set_b = factor_sets[b] # Identical object if a==b, but logic holds
                        
                        for val in set_a:
                            graph_nodes.append({"id": val, "label": str(val), "group": group_id})
                        if a != b:
                            for val in set_b:
                                graph_nodes.append({"id": val, "label": str(val), "group": group_id})

                        if a == b:
                            for i in range(len(set_a)):
                                for j in range(i + 1, len(set_a)):
                                    graph_edges.append({"from": set_a[i], "to": set_a[j]})
                        else:
                            for u in set_a:
                                for v in set_b:
                                    graph_edges.append({"from": u, "to": v})
                    
                    group_id += 1

                    if a == b:
                        components.append(f"C_{{{len_a}}}")
                        w += len_a
                    else:
                        set_b = factor_sets[b]
                        len_b = len(set_b)
                        low = min(len_a, len_b)
                        high = max(len_a, len_b)
                        components.append(f"K_{{{low},{high}}}")
                        w += (len_a + len_b)

            comp_str = ", ".join(components)
            g_data = None
            if curr_n < GRAPH_THRESHOLD:
                unique_nodes = {node['id']: node for node in graph_nodes}.values()
                g_data = {"nodes": list(unique_nodes), "edges": graph_edges}

            c.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?)", 
                      (curr_n, comp_str, w, json.dumps(g_data), 0))
            
            curr_n += 1
        
        conn.commit()
        print(f"Processed up to n={curr_n-1}")

    print("Optimizing database size (VACUUM)... please wait.")
    c.execute("VACUUM")
    conn.close()
    print("Database closed and optimized.")

if __name__ == "__main__":
    generate_data()
