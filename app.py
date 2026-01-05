import os
import json
import functools
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify, request, send_file
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import run_migrations

app = Flask(__name__)

# Cache for performance optimization
@functools.lru_cache(maxsize=2048)
def calculate_time_to_reach_cost_cached(cps_key, cost_int):
    """Cached version of time calculation for better performance"""
    cps = cps_key / 1000.0
    cost = cost_int
    
    if cps <= 0:
        return float('inf')
    
    video_cycle = [10, 10, 20, 20, 30]
    cookies_per_cycle = cps * (5 * 70 + sum(video_cycle) * 60)
    time_per_cycle = 5 * 70 / 60
    
    full_cycles = int(cost / cookies_per_cycle) if cookies_per_cycle > 0 else 0
    remaining_cost = cost - (full_cycles * cookies_per_cycle)
    total_time = full_cycles * time_per_cycle
    
    if remaining_cost > 0:
        video_index = 0
        total_cookies = 0
        while total_cookies < remaining_cost and video_index < 5:
            total_cookies += cps * 70
            total_time += 70 / 60
            total_cookies += cps * video_cycle[video_index] * 60
            video_index += 1
    
    return total_time

def load_upgrades(file_path='cookie_clicker_upgrades.json'):
    """Load upgrades from the SQLite DB. If DB is empty, init from JSON file."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT name, price, level, cps FROM upgrades ORDER BY position ASC")
    rows = cur.fetchall()
    conn.close()
    upgrades = []
    for r in rows:
        upgrades.append({
            "name": r[0],
            "price": r[1],
            "level": r[2],
            "cps": r[3]
        })
    return upgrades

def save_upgrades(upgrades, file_path='cookie_clicker_upgrades.json'):
    """Save a list of upgrades into the DB (upsert)."""
    conn = get_db_connection()
    cur = conn.cursor()
    for i, u in enumerate(upgrades):
        cur.execute(
            "INSERT INTO upgrades (name, price, level, cps, position) VALUES (?,?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET price=excluded.price, level=excluded.level, cps=excluded.cps, position=excluded.position",
            (u['name'], u['price'], int(u.get('level', 0)), u['cps'], i)
        )
    conn.commit()
    conn.close()

def update_upgrade_level(name, level):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE upgrades SET level = ? WHERE name = ?", (int(level), name))
    conn.commit()
    conn.close()

def ensure_dirs():
    base = os.path.dirname(__file__)
    backups = os.path.join(base, 'backups')
    os.makedirs(backups, exist_ok=True)
    os.makedirs(os.path.join(base, 'simulations'), exist_ok=True)

def create_db_backup():
    """Create a timestamped backup of data.db and return the backup filename."""
    ensure_dirs()
    db_path = os.path.join(os.path.dirname(__file__), 'data.db')
    if not os.path.exists(db_path):
        return None
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f'data_backup_{timestamp}.db'
    backup_path = os.path.join(os.path.dirname(__file__), 'backups', backup_name)
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        return backup_name
    except Exception as e:
        print(f'Backup creation failed: {e}')
        return None

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'data.db')
    conn = sqlite3.connect(db_path, check_same_thread=False)
    return conn

def init_db(json_path='cookie_clicker_upgrades.json'):
    """Ensure DB schema and seed defaults using Alembic migrations.

    If Alembic or SQLAlchemy are not available, fall back to creating the
    `upgrades` table directly so the application remains usable.
    """
    try:
        run_migrations.upgrade_head()
    except Exception as e:
        # Fallback: create upgrades table if migrations can't run
        db_path = os.path.join(os.path.dirname(__file__), 'data.db')
        conn = sqlite3.connect(db_path, check_same_thread=False)
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS upgrades (
                name TEXT PRIMARY KEY,
                price REAL NOT NULL,
                level INTEGER NOT NULL DEFAULT 0,
                cps REAL NOT NULL DEFAULT 0,
                position INTEGER NOT NULL DEFAULT 0
            )
        ''')
        # Populate from seeds (prefer seeds.py, fallback to JSON file)
        try:
            import importlib.util
            spec = importlib.util.find_spec('seeds')
            if spec is not None:
                import seeds as seeds_mod
                data = getattr(seeds_mod, 'SEEDS', [])
            else:
                data = None
        except Exception:
            data = None

        if not data:
            base = os.path.dirname(__file__)
            json_path = os.path.join(base, 'cookie_clicker_upgrades.json')
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    data = []
            else:
                data = []

        # Insert or update rows according to seed data (use seed_level for initial level)
        for pos, item in enumerate(data):
            name = item.get('name')
            price = float(item.get('price', 0))
            cps = float(item.get('cps', 0))
            seed_level = int(item.get('seed_level', item.get('level', 0)))
            cur.execute(
                "INSERT OR REPLACE INTO upgrades (name, price, level, cps, position) VALUES (?,?,?,?,?)",
                (name, price, seed_level, cps, pos)
            )

        conn.commit()
        conn.close()

def calculate_total_cps(upgrades):
    return sum(u["level"] * u["cps"] for u in upgrades if u["level"] > 0)

def compute_upgrade_value(upgrade):
    truncated_price = int(upgrade['price'] * (1.3 ** upgrade['level']))
    return upgrade['cps'] / truncated_price

def get_best_upgrade(upgrades):
    """Calculate and return the best upgrade with efficiency metrics"""
    unlocked = [u for i, u in enumerate(upgrades) 
                if u["level"] > 0 or i == 0 or (u["level"] == 0 and upgrades[i - 1]["level"] >= 1)]
    
    if not unlocked:
        return None
    
    total_cps = calculate_total_cps(upgrades)
    candidates = []
    
    for u in unlocked:
        truncated_price = int(u['price'] * (1.3 ** u['level']))
        time_to_reach = calculate_time_to_reach_cost_cached(int(total_cps * 1000), int(truncated_price))
        
        if time_to_reach != float('inf') and time_to_reach > 0:
            value = compute_upgrade_value(u)
            efficiency_ratio = value / time_to_reach if time_to_reach > 0 else 0
            candidates.append({
                "name": u["name"],
                "level": u["level"],
                "price": truncated_price,
                "cps": u["cps"],
                "value": value,
                "time": time_to_reach,
                "efficiency": efficiency_ratio
            })
    
    if not candidates:
        return None
    
    return max(candidates, key=lambda c: c['efficiency'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/upgrades')
def get_upgrades():
    upgrades = load_upgrades()
    total_cps = calculate_total_cps(upgrades)
    best = get_best_upgrade(upgrades)
    
    # Calculate metrics for all unlocked upgrades
    unlocked_with_metrics = []
    for i, u in enumerate(upgrades):
        if u["level"] > 0 or i == 0 or (u["level"] == 0 and upgrades[i - 1]["level"] >= 1):
            price = int(u['price'] * (1.3 ** u['level']))
            time = calculate_time_to_reach_cost_cached(int(total_cps * 1000), int(price))
            value = compute_upgrade_value(u)
            
            unlocked_with_metrics.append({
                **u,
                "current_price": price,
                "time_to_reach": time if time != float('inf') else None,
                "value": value,
                "is_best": best and u["name"] == best["name"]
            })
    
    return jsonify({
        "upgrades": unlocked_with_metrics,
        "total_cps": total_cps,
        "best_upgrade": best
    })

@app.route('/api/upgrade/<upgrade_name>', methods=['POST'])
def purchase_upgrade(upgrade_name):
    try:
        if not upgrade_name:
            return jsonify({"success": False, "error": "Upgrade name required"}), 400
        
        upgrades = load_upgrades()
        for u in upgrades:
            if u["name"] == upgrade_name:
                new_level = int(u.get('level', 0)) + 1
                update_upgrade_level(upgrade_name, new_level)
                u['level'] = new_level
                return jsonify({"success": True, "upgrade": u})
        
        return jsonify({"success": False, "error": "Upgrade not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": f"Purchase failed: {str(e)}"}), 500


@app.route('/api/upgrade/<upgrade_name>/decrease', methods=['POST'])
def decrease_upgrade(upgrade_name):
    try:
        if not upgrade_name:
            return jsonify({"success": False, "error": "Upgrade name required"}), 400

        upgrades = load_upgrades()
        for u in upgrades:
            if u["name"] == upgrade_name:
                current = int(u.get('level', 0))
                if current <= 0:
                    return jsonify({"success": False, "error": "Level already zero"}), 400
                new_level = current - 1
                update_upgrade_level(upgrade_name, new_level)
                u['level'] = new_level
                return jsonify({"success": True, "upgrade": u})

        return jsonify({"success": False, "error": "Upgrade not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": f"Decrease failed: {str(e)}"}), 500


@app.route('/api/reset', methods=['POST'])
def reset_upgrades():
    try:
        # Create a backup before reset
        backup_name = create_db_backup()
        if not backup_name:
            return jsonify({"success": False, "error": "Failed to create backup before reset"}), 500
        # Reset levels to seed defaults (prefer seeds.py, fallback to JSON file)
        try:
            import importlib.util
            spec = importlib.util.find_spec('seeds')
            if spec is not None:
                import seeds as seeds_mod
                seed_data = getattr(seeds_mod, 'SEEDS', [])
            else:
                seed_data = None
        except Exception:
            seed_data = None

        if not seed_data:
            base = os.path.dirname(__file__)
            json_path = os.path.join(base, 'cookie_clicker_upgrades.json')
            if os.path.exists(json_path):
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        seed_data = json.load(f)
                except Exception:
                    seed_data = []
            else:
                seed_data = []

        conn = get_db_connection()
        cur = conn.cursor()

        # If seed_data is empty, fall back to zeroing levels
        if not seed_data:
            cur.execute('UPDATE upgrades SET level = 0')
        else:
            # Build a mapping from name -> seed_level and update each row
            for item in seed_data:
                name = item.get('name')
                seed_level = int(item.get('seed_level', item.get('level', 0)))
                # Ensure row exists and set level accordingly
                cur.execute(
                    "INSERT OR REPLACE INTO upgrades (name, price, level, cps, position) "
                    "VALUES (:name, COALESCE((SELECT price FROM upgrades WHERE name=:name), :price), :level, "
                    "COALESCE((SELECT cps FROM upgrades WHERE name=:name), :cps), COALESCE((SELECT position FROM upgrades WHERE name=:name), :pos))",
                    {
                        'name': name,
                        'price': float(item.get('price', 0)),
                        'level': seed_level,
                        'cps': float(item.get('cps', 0)),
                        'pos': item.get('position', 0)
                    }
                )

        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Upgrades reset to seed defaults", "backup": backup_name})
    except Exception as e:
        return jsonify({"success": False, "error": f"Reset failed: {str(e)}"}), 500

@app.route('/api/simulate', methods=['POST'])
def simulate():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        total_purchases = data.get('purchases', 100)
        
        # Validation
        if not isinstance(total_purchases, int) or total_purchases < 1 or total_purchases > 10000:
            return jsonify({"success": False, "error": "Invalid purchase count (1-10000)"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
    upgrades = load_upgrades()
    
    # Reset levels for simulation
    for u in upgrades:
        u["level"] = 0
    upgrades[0]["level"] = 1
    
    total_upgrades = 0
    purchase_plan = {u["name"]: 0 for u in upgrades}
    time_spent_per_upgrade = {u["name"]: 0 for u in upgrades}
    cost_per_upgrade = {u["name"]: 0 for u in upgrades}
    total_time_spent = 0
    total_cookies_spent = 0
    
    # Track progression for timeline
    timeline = []
    
    while total_upgrades < total_purchases:
        total_cps = calculate_total_cps(upgrades)
        best = get_best_upgrade(upgrades)
        
        if not best:
            break
        
        best_upgrade_price = int(best['price'])
        time_to_reach = calculate_time_to_reach_cost_cached(int(total_cps * 1000), int(best_upgrade_price))
        
        if time_to_reach == float('inf'):
            break
        
        # Update the upgrade
        for u in upgrades:
            if u["name"] == best["name"]:
                u["level"] += 1
                purchase_plan[u["name"]] += 1
                time_spent_per_upgrade[u["name"]] += time_to_reach
                cost_per_upgrade[u["name"]] += best_upgrade_price
                total_time_spent += time_to_reach
                total_cookies_spent += best_upgrade_price
                total_upgrades += 1
                
                # Record timeline point every 10 purchases
                if total_upgrades % 10 == 0 or total_upgrades == 1:
                    timeline.append({
                        "purchase": total_upgrades,
                        "cps": calculate_total_cps(upgrades),
                        "time": total_time_spent,
                        "upgrade": u["name"]
                    })
                break
    
    final_cps = calculate_total_cps(upgrades)
    
    # Prepare results
    results = []
    for u in upgrades:
        count = purchase_plan[u["name"]]
        if count > 0:
            contribution = u["cps"] * count
            percentage = (contribution / final_cps * 100) if final_cps > 0 else 0
            time_percentage = (time_spent_per_upgrade[u["name"]] / total_time_spent * 100) if total_time_spent > 0 else 0
            
            results.append({
                "name": u["name"],
                "purchases": count,
                "total_cost": cost_per_upgrade[u["name"]],
                "avg_cost": cost_per_upgrade[u["name"]] / count if count > 0 else 0,
                "cps_contribution": contribution,
                "cps_percentage": percentage,
                "time_spent": time_spent_per_upgrade[u["name"]],
                "time_percentage": time_percentage
            })
    
    # Save simulation results with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    simulation_data = {
        "timestamp": timestamp,
        "total_purchases": total_upgrades,
        "final_cps": final_cps,
        "total_time": total_time_spent,
        "total_cookies": total_cookies_spent,
        "results": results,
        "timeline": timeline
    }
    
    # Save to JSON
    os.makedirs('simulations', exist_ok=True)
    with open(f'simulations/simulation_{timestamp}.json', 'w') as f:
        json.dump(simulation_data, f, indent=4)
    
    # Save to CSV
    df = pd.DataFrame(results)
    df.to_csv(f'simulations/simulation_{timestamp}.csv', index=False)
    
    return jsonify(simulation_data)


@app.route('/api/backup', methods=['POST'])
def create_backup_endpoint():
    try:
        name = create_db_backup()
        if not name:
            return jsonify({"success": False, "error": "Backup failed or DB not found"}), 500
        url = f'/api/backup/{name}'
        return jsonify({"success": True, "filename": name, "url": url})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/backups')
def list_backups():
    base = os.path.dirname(__file__)
    backups_dir = os.path.join(base, 'backups')
    if not os.path.exists(backups_dir):
        return jsonify([])
    files = [f for f in os.listdir(backups_dir) if f.endswith('.db')]
    files_sorted = sorted(files, reverse=True)
    items = []
    for f in files_sorted:
        p = os.path.join(backups_dir, f)
        items.append({
            'filename': f,
            'size': os.path.getsize(p),
            'path': f'/api/backup/{f}'
        })
    return jsonify(items)


@app.route('/api/backup/<filename>')
def download_backup(filename):
    base = os.path.dirname(__file__)
    backups_dir = os.path.join(base, 'backups')
    path = os.path.join(backups_dir, filename)
    if not os.path.exists(path):
        return jsonify({"success": False, "error": "Backup not found"}), 404
    return send_file(path, as_attachment=True)

@app.route('/api/charts/<chart_type>')
def get_chart(chart_type):
    upgrades = load_upgrades()
    total_cps = calculate_total_cps(upgrades)
    
    if chart_type == 'current':
        # Current CPS distribution
        unlocked = [u for u in upgrades if u["level"] > 0]
        if not unlocked:
            return jsonify({"error": "No data"}), 404
        
        names = [u["name"] for u in unlocked]
        contributions = [u["level"] * u["cps"] for u in unlocked]
        percentages = [(c / total_cps * 100) if total_cps > 0 else 0 for c in contributions]
        levels = [u["level"] for u in unlocked]
        
        fig = go.Figure(go.Bar(
            x=percentages,
            y=names,
            orientation='h',
            text=[f'{p:.1f}% (lvl {l})' for p, l in zip(percentages, levels)],
            textposition='outside',
            marker=dict(
                color=percentages,
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title="% CPS")
            )
        ))
        
        fig.update_layout(
            title=f'Current CPS Distribution<br>Total: {total_cps:,.0f} cookies/sec',
            xaxis_title='% of Total CPS',
            yaxis_title='Upgrade',
            height=max(400, len(unlocked) * 40),
            template='plotly_dark'
        )
        
        return jsonify(fig.to_json())
    
    return jsonify({"error": "Invalid chart type"}), 400

@app.route('/api/simulation-charts', methods=['POST'])
def get_simulation_charts():
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "error": "No data provided"}), 400
        
        results = data.get('results', [])
        timeline = data.get('timeline', [])
        final_cps = data.get('final_cps', 0)
        total_time = data.get('total_time', 0)
        
        if not results:
            return jsonify({"success": False, "error": "No results to display"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    
    # Chart 1: CPS Distribution
    names = [r['name'] for r in results]
    percentages = [r['cps_percentage'] for r in results]
    purchases = [r['purchases'] for r in results]
    
    fig1 = go.Figure(go.Bar(
        x=percentages,
        y=names,
        orientation='h',
        text=[f'{p:.1f}% ({c}x)' for p, c in zip(percentages, purchases)],
        textposition='outside',
        marker=dict(
            color=percentages,
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="% CPS")
        )
    ))
    
    fig1.update_layout(
        title=f'CPS Distribution<br>Total: {final_cps:,.0f} cookies/sec',
        xaxis_title='% of Total CPS',
        yaxis_title='Upgrade',
        height=max(400, len(results) * 35),
        template='plotly_dark'
    )
    
    # Chart 2: Purchases vs Time Investment
    times = [r['time_spent'] for r in results]
    
    fig2 = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig2.add_trace(
        go.Bar(name='Purchases', x=names, y=purchases, marker_color='lightblue'),
        secondary_y=False
    )
    
    fig2.add_trace(
        go.Scatter(name='Time Spent', x=names, y=times, mode='markers',
                   marker=dict(size=12, color='red', symbol='diamond')),
        secondary_y=True
    )
    
    fig2.update_xaxes(title_text="Upgrades", tickangle=45)
    fig2.update_yaxes(title_text="Number of Purchases", secondary_y=False)
    fig2.update_yaxes(title_text="Time Spent (minutes)", secondary_y=True)
    
    fig2.update_layout(
        title='Purchases vs Time Investment',
        height=500,
        template='plotly_dark'
    )
    
    # Chart 3: CPS Timeline (progression over time)
    if timeline:
        purchase_points = [t['purchase'] for t in timeline]
        cps_values = [t['cps'] for t in timeline]
        time_points = [t['time'] for t in timeline]
        
        fig3 = make_subplots(rows=1, cols=2,
                            subplot_titles=('CPS Growth Over Purchases', 'CPS Growth Over Time'))
        
        fig3.add_trace(
            go.Scatter(x=purchase_points, y=cps_values, mode='lines+markers',
                      name='CPS', line=dict(color='cyan', width=3)),
            row=1, col=1
        )
        
        fig3.add_trace(
            go.Scatter(x=time_points, y=cps_values, mode='lines+markers',
                      name='CPS', line=dict(color='magenta', width=3), showlegend=False),
            row=1, col=2
        )
        
        fig3.update_xaxes(title_text="Purchases", row=1, col=1)
        fig3.update_xaxes(title_text="Time (minutes)", row=1, col=2)
        fig3.update_yaxes(title_text="CPS", type="log", row=1, col=1)
        fig3.update_yaxes(title_text="CPS", type="log", row=1, col=2)
        
        fig3.update_layout(
            height=400,
            template='plotly_dark',
            title_text='CPS Progression Analysis'
        )
    else:
        fig3 = None
    
    # Chart 4: Cost vs CPS Heatmap
    costs = [r['avg_cost'] for r in results]
    cps_contribs = [r['cps_contribution'] for r in results]
    
    fig4 = go.Figure(go.Scatter(
        x=costs,
        y=cps_contribs,
        mode='markers+text',
        text=names,
        textposition='top center',
        marker=dict(
            size=[r['purchases'] * 2 for r in results],
            color=percentages,
            colorscale='Plasma',
            showscale=True,
            colorbar=dict(title="% CPS")
        )
    ))
    
    fig4.update_layout(
        title='Cost vs CPS Contribution<br>(Bubble size = purchases)',
        xaxis_title='Average Cost per Purchase',
        yaxis_title='Total CPS Contribution',
        xaxis_type='log',
        yaxis_type='log',
        height=500,
        template='plotly_dark'
    )
    
    return jsonify({
        "success": True,
        "chart1": fig1.to_json(),
        "chart2": fig2.to_json(),
        "chart3": fig3.to_json() if fig3 else None,
        "chart4": fig4.to_json()
    })

@app.route('/api/export/<format>')
def export_data(format):
    upgrades = load_upgrades()
    
    if format == 'csv':
        df = pd.DataFrame(upgrades)
        filepath = 'current_upgrades.csv'
        df.to_csv(filepath, index=False)
        return send_file(filepath, as_attachment=True)
    
    elif format == 'json':
        filepath = 'current_upgrades.json'
        with open(filepath, 'w') as f:
            json.dump(upgrades, f, indent=4)
        return send_file(filepath, as_attachment=True)
    
    return jsonify({"error": "Invalid format"}), 400

@app.route('/api/simulations')
def list_simulations():
    if not os.path.exists('simulations'):
        return jsonify([])
    
    files = [f for f in os.listdir('simulations') if f.endswith('.json')]
    simulations = []
    
    for file in sorted(files, reverse=True):
        with open(f'simulations/{file}', 'r') as f:
            data = json.load(f)
            simulations.append({
                "filename": file,
                "timestamp": data.get("timestamp"),
                "total_purchases": data.get("total_purchases"),
                "final_cps": data.get("final_cps")
            })
    
    return jsonify(simulations)

if __name__ == '__main__':
    # Ensure DB initialized (populate from JSON on first run)
    init_db()
    app.run(debug=True, port=5000)
