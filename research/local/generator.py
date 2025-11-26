import sqlite3
import math
import json
import signal
import sys
import time

DB_NAME = "graph_data.db"
running = True

def signal_handler(sig, frame):
    global running
    print("\nStopping generator... finishing current batch.")
    running = False

signal.signal(signal.SIGINT, signal_handler)

def get_factors(n):
    """Returns factors of n excluding 1 and n, sorted descending."""
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
    conn.commit()

    # Get last n
    c.execute("SELECT MAX(n) FROM records")
    row = c.fetchone()
    start_n = (row[0] + 1) if row[0] is not None else 4
    
    print(f"Starting generation from n = {start_n}. Press Ctrl+C to stop.")

    curr_n = start_n
    
    while running:
        # Transaction batch
        for _ in range(100): 
            if not running: break
            
            # 1. Check Prime
            if is_prime(curr_n):
                c.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?)", 
                          (curr_n, "", 0, json.dumps(None), 1))
                curr_n += 1
                continue

            # 2. Factorization & Set Generation
            factors = get_factors(curr_n)
            factor_sets = {} # Map factor -> List of numbers
            seen_multiples = set()
            
            # Largest to smallest factor logic
            for f in factors:
                multiples = []
                # Range: f, 2f, 3f ... < n
                for m in range(f, curr_n, f):
                    if m not in seen_multiples:
                        multiples.append(m)
                        seen_multiples.add(m)
                factor_sets[f] = multiples

            # 3. Pair up factorizations
            components = [] # List of tuples ("K", sizeA, sizeB) or ("C", size)
            w = 0
            
            # We need to find pairs (a,b) such that a*b = n.
            # To avoid duplicates (e.g. 2*27 and 27*2), we iterate through our sorted factors list
            # and verify the pair.
            
            processed_pairs = set()

            graph_nodes = []
            graph_edges = []
            group_id = 0

            for a in factors:
                b = curr_n // a
                if b in factors: # Valid pair excluding 1,n
                    # Enforce ordering to avoid duplicates: a >= b
                    if a < b: continue
                    
                    pair_sig = (a, b)
                    if pair_sig in processed_pairs: continue
                    processed_pairs.add(pair_sig)

                    set_a = factor_sets[a]
                    set_b = factor_sets[b]
                    len_a = len(set_a)
                    len_b = len(set_b)

                    # Graphing Data Generation (if n < 500)
                    if curr_n < 500:
                        # Add nodes with group IDs
                        # We tag nodes with a prefix to make them unique per component visualization if needed,
                        # but typically we want the actual numbers. 
                        # However, since a number can appear in only ONE set globally (due to skipping),
                        # we can just treat them as unique IDs.
                        
                        # Note: In the K_xy case, set_a and set_b are disjoint because of the skipping rule?
                        # Actually, wait. The skipping rule is global for 'seen_multiples'.
                        # If 18 is in set(18), it cannot be in set(9).
                        # So set_a and set_b are disjoint sets of integers.
                        
                        # Add nodes
                        for val in set_a:
                            graph_nodes.append({"id": val, "label": str(val), "group": group_id})
                        for val in set_b:
                            # If a == b, set_a is set_b, don't re-add
                            if a != b:
                                graph_nodes.append({"id": val, "label": str(val), "group": group_id})

                        # Add edges
                        if a == b:
                            # Complete graph on set_a
                            # Connect every node to every other node
                            for i in range(len(set_a)):
                                for j in range(i + 1, len(set_a)):
                                    graph_edges.append({"from": set_a[i], "to": set_a[j]})
                        else:
                            # Complete Bipartite between set_a and set_b
                            for u in set_a:
                                for v in set_b:
                                    graph_edges.append({"from": u, "to": v})
                    
                    group_id += 1

                    if a == b:
                        # Perfect Square Case -> C_{m}
                        components.append(f"C_{{{len_a}}}")
                        w += len_a
                    else:
                        # Bipartite Case -> K_{x,y}
                        # We store K_{min,max} for consistency in string, 
                        # but math-wise order doesn't matter.
                        low = min(len_a, len_b)
                        high = max(len_a, len_b)
                        components.append(f"K_{{{low},{high}}}")
                        w += (len_a + len_b)

            # Format data for DB
            comp_str = ", ".join(components)
            g_data = None
            if curr_n < 500:
                # Deduplicate nodes just in case (though logic suggests disjointness)
                unique_nodes = {node['id']: node for node in graph_nodes}.values()
                g_data = {"nodes": list(unique_nodes), "edges": graph_edges}

            c.execute("INSERT INTO records VALUES (?, ?, ?, ?, ?)", 
                      (curr_n, comp_str, w, json.dumps(g_data), 0))
            
            curr_n += 1
        
        conn.commit()
        print(f"Processed up to n={curr_n-1}")

    conn.close()
    print("Database closed.")

if __name__ == "__main__":
    generate_data()
