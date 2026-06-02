import mysql.connector
import random
import time
from datetime import datetime

# ── DB connection ──────────────────────────────────────────────
DB = {
    "host": "localhost",
    "user": "root",
    "password": "yourpassword",   # change this to your MySQL root password
    "database": "robot_fleet"
}

LOCATIONS = [
    "Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E",
    "Dock-A", "Dock-B", "Charging-Bay", "Warehouse-1", "Warehouse-2"
]

INCIDENT_TYPES = [
    ("Battery Low",        "critical"),
    ("Obstacle Detected",  "medium"),
    ("Navigation Error",   "medium"),
    ("Sensor Failure",     "critical"),
    ("Path Blocked",       "low"),
    ("Communication Lost", "critical"),
    ("Motor Overheating",  "medium"),
    ("Emergency Stop",     "low"),
]

def get_db():
    return mysql.connector.connect(**DB)

def get_robots(cursor):
    cursor.execute("SELECT id, name, status, battery FROM robots")
    return cursor.fetchall()

def update_robot(cursor, robot_id, status, battery, location):
    cursor.execute("""
        UPDATE robots
        SET status = %s, battery = %s, location = %s, last_heartbeat = NOW()
        WHERE id = %s
    """, (status, battery, location, robot_id))

def insert_metrics(cursor, robot_id, battery):
    cpu_temp = round(random.uniform(38.0, 72.0), 2)
    speed    = round(random.uniform(0.0, 1.8), 2)
    cursor.execute("""
        INSERT INTO metrics (robot_id, battery, cpu_temp, speed_ms)
        VALUES (%s, %s, %s, %s)
    """, (robot_id, battery, cpu_temp, speed))

def create_incident(cursor, robot_id, inc_type, severity, note):
    cursor.execute("""
        INSERT INTO incidents (robot_id, type, severity, notes)
        VALUES (%s, %s, %s, %s)
    """, (robot_id, inc_type, severity, note))
    print(f"  [INCIDENT] Robot {robot_id} → {inc_type} ({severity})")

def resolve_old_incidents(cursor):
    # Randomly resolve incidents older than 2 minutes that are still open
    cursor.execute("""
        UPDATE incidents
        SET resolved_at = NOW()
        WHERE resolved_at IS NULL
          AND created_at < NOW() - INTERVAL 2 MINUTE
          AND RAND() < 0.4
    """)

def start_mission(cursor, robot_id):
    cursor.execute("""
        INSERT INTO missions (robot_id, status, distance_m)
        VALUES (%s, 'running', 0)
    """, (robot_id,))
    return cursor.lastrowid

def complete_mission(cursor, robot_id):
    # Find the latest running mission for this robot and complete it
    cursor.execute("""
        UPDATE missions
        SET status = %s, end_time = NOW(), distance_m = %s
        WHERE robot_id = %s AND status = 'running'
        ORDER BY start_time DESC
        LIMIT 1
    """, (
        random.choice(["completed", "completed", "completed", "failed"]),
        round(random.uniform(10.0, 200.0), 1),
        robot_id
    ))

def simulate():
    print("=" * 50)
    print("  ROC-Sim  —  AMR Fleet Operations Monitor")
    print("  Ati Motors ROC Simulation")
    print("=" * 50)
    print(f"  Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("  Simulating 5 robots. Press Ctrl+C to stop.\n")

    active_missions = {}   # robot_id -> mission_id

    while True:
        try:
            db     = get_db()
            cursor = db.cursor(dictionary=True)

            robots = get_robots(cursor)

            for robot in robots:
                rid     = robot["id"]
                battery = robot["battery"]
                status  = robot["status"]

                # ── Battery drain ──────────────────────────────
                if status in ("active", "error"):
                    battery = max(0, battery - random.randint(1, 4))
                elif status == "idle":
                    battery = min(100, battery + random.randint(0, 2))

                # ── Charging at dock brings battery up fast ────
                if battery < 20 and status != "error":
                    status  = "idle"
                    battery = min(100, battery + random.randint(5, 10))
                    print(f"  [CHARGE]   Robot {rid} low battery — sent to charging bay")

                # ── Decide next status ─────────────────────────
                roll = random.random()
                if battery > 30:
                    if roll < 0.55:
                        new_status = "active"
                    elif roll < 0.75:
                        new_status = "idle"
                    elif roll < 0.88:
                        new_status = "active"
                    elif roll < 0.95:
                        new_status = "error"
                    else:
                        new_status = "offline"
                else:
                    new_status = "idle"   # low battery → keep idle / charging

                location = random.choice(LOCATIONS)
                update_robot(cursor, rid, new_status, battery, location)
                insert_metrics(cursor, rid, battery)

                # ── Mission tracking ───────────────────────────
                if new_status == "active" and rid not in active_missions:
                    mid = start_mission(cursor, rid)
                    active_missions[rid] = mid
                    print(f"  [MISSION]  Robot {rid} started mission #{mid}")

                elif new_status != "active" and rid in active_missions:
                    complete_mission(cursor, rid)
                    print(f"  [MISSION]  Robot {rid} ended mission #{active_missions[rid]}")
                    del active_missions[rid]

                # ── Incident generation ────────────────────────
                inc_chance = 0.08   # 8% chance per robot per cycle
                if battery < 15:
                    inc_chance = 0.6
                elif new_status == "error":
                    inc_chance = 0.5
                elif new_status == "offline":
                    inc_chance = 0.4

                if random.random() < inc_chance:
                    if battery < 15:
                        inc_type, severity = "Battery Low", "critical"
                    elif new_status == "error":
                        inc_type, severity = random.choice([
                            ("Sensor Failure", "critical"),
                            ("Motor Overheating", "medium"),
                            ("Navigation Error", "medium")
                        ])
                    elif new_status == "offline":
                        inc_type, severity = "Communication Lost", "critical"
                    else:
                        inc_type, severity = random.choice(INCIDENT_TYPES)

                    note = (f"Auto-detected by simulator at "
                            f"{datetime.now().strftime('%H:%M:%S')} — "
                            f"battery={battery}%, location={location}")
                    create_incident(cursor, rid, inc_type, severity, note)

            # ── Resolve old incidents ──────────────────────────
            resolve_old_incidents(cursor)

            db.commit()
            cursor.close()
            db.close()

            print(f"  [TICK] {datetime.now().strftime('%H:%M:%S')} — fleet updated\n")
            time.sleep(5)

        except KeyboardInterrupt:
            print("\n  Simulator stopped.")
            break
        except mysql.connector.Error as e:
            print(f"  [DB ERROR] {e}")
            time.sleep(5)

if __name__ == "__main__":
    simulate()