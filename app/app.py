from flask import Flask, render_template, jsonify
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)

DB = {
    "host":     "localhost",
    "user":     "root",
    "password": "yourpassword",   # change this to your MySQL root password
    "database": "robot_fleet"
}

def get_db():
    return mysql.connector.connect(**DB)

# ── Home — serve the dashboard ────────────────────────────────
@app.route("/")
def index():
    return render_template("dashboard.html")

# ── /fleet — all robots with current status ───────────────────
@app.route("/fleet")
def fleet():
    db     = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            r.id,
            r.name,
            r.model,
            r.status,
            r.battery,
            r.location,
            r.last_heartbeat,
            COUNT(CASE WHEN i.resolved_at IS NULL THEN 1 END) AS open_incidents
        FROM robots r
        LEFT JOIN incidents i ON r.id = i.robot_id
        GROUP BY r.id
        ORDER BY r.id
    """)
    robots = cursor.fetchall()
    cursor.close()
    db.close()
    # Convert datetime to string for JSON
    for r in robots:
        if r["last_heartbeat"]:
            r["last_heartbeat"] = r["last_heartbeat"].strftime("%H:%M:%S")
    return jsonify(robots)

# ── /incidents — open (unresolved) incidents ──────────────────
@app.route("/incidents")
def incidents():
    db     = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            i.id,
            r.name  AS robot_name,
            i.type,
            i.severity,
            i.created_at,
            i.notes
        FROM incidents i
        INNER JOIN robots r ON i.robot_id = r.id
        WHERE i.resolved_at IS NULL
        ORDER BY
            FIELD(i.severity, 'critical', 'medium', 'low'),
            i.created_at DESC
        LIMIT 20
    """)
    incidents = cursor.fetchall()
    cursor.close()
    db.close()
    for inc in incidents:
        if inc["created_at"]:
            inc["created_at"] = inc["created_at"].strftime("%H:%M:%S")
    return jsonify(incidents)

# ── /kpis — computed operational metrics ─────────────────────
@app.route("/kpis")
def kpis():
    db     = get_db()
    cursor = db.cursor(dictionary=True)

    # Total robots and their statuses
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(status = 'active')  AS active,
            SUM(status = 'idle')    AS idle,
            SUM(status = 'offline') AS offline,
            SUM(status = 'error')   AS error
        FROM robots
    """)
    fleet_status = cursor.fetchone()

    # Fleet uptime % = (active + idle) / total * 100
    total   = fleet_status["total"] or 1
    up      = (fleet_status["active"] or 0) + (fleet_status["idle"] or 0)
    uptime  = round((up / total) * 100, 1)

    # Mission success rate
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(status = 'completed') AS completed,
            SUM(status = 'failed')    AS failed
        FROM missions
    """)
    missions = cursor.fetchone()
    total_m  = missions["total"] or 1
    success  = round(((missions["completed"] or 0) / total_m) * 100, 1)

    # MTTR — average minutes to resolve an incident
    cursor.execute("""
        SELECT
            AVG(TIMESTAMPDIFF(MINUTE, created_at, resolved_at)) AS avg_minutes
        FROM incidents
        WHERE resolved_at IS NOT NULL
    """)
    mttr_row = cursor.fetchone()
    mttr     = round(mttr_row["avg_minutes"] or 0, 1)

    # Open incidents by severity
    cursor.execute("""
        SELECT severity, COUNT(*) AS count
        FROM incidents
        WHERE resolved_at IS NULL
        GROUP BY severity
    """)
    open_inc = {row["severity"]: row["count"] for row in cursor.fetchall()}

    # SLA compliance — incidents resolved within 10 minutes
    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(TIMESTAMPDIFF(MINUTE, created_at, resolved_at) <= 10) AS within_sla
        FROM incidents
        WHERE resolved_at IS NOT NULL
    """)
    sla_row = cursor.fetchone()
    sla_total  = sla_row["total"] or 1
    sla_pct    = round(((sla_row["within_sla"] or 0) / sla_total) * 100, 1)

    cursor.close()
    db.close()

    return jsonify({
        "uptime_pct":       uptime,
        "active_robots":    fleet_status["active"]  or 0,
        "idle_robots":      fleet_status["idle"]    or 0,
        "offline_robots":   fleet_status["offline"] or 0,
        "error_robots":     fleet_status["error"]   or 0,
        "mission_success":  success,
        "total_missions":   missions["total"],
        "mttr_minutes":     mttr,
        "sla_compliance":   sla_pct,
        "open_critical":    open_inc.get("critical", 0),
        "open_medium":      open_inc.get("medium",   0),
        "open_low":         open_inc.get("low",      0),
    })

# ── /metrics/latest — latest telemetry per robot ─────────────
@app.route("/metrics/latest")
def metrics_latest():
    db     = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("""
        SELECT m.robot_id, r.name, m.battery, m.cpu_temp, m.speed_ms, m.recorded_at
        FROM metrics m
        INNER JOIN robots r ON m.robot_id = r.id
        WHERE m.recorded_at = (
            SELECT MAX(m2.recorded_at)
            FROM metrics m2
            WHERE m2.robot_id = m.robot_id
        )
        ORDER BY m.robot_id
    """)
    rows = cursor.fetchall()
    cursor.close()
    db.close()
    for row in rows:
        if row["recorded_at"]:
            row["recorded_at"] = row["recorded_at"].strftime("%H:%M:%S")
    return jsonify(rows)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)