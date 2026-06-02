#!/bin/bash

# ── Config ────────────────────────────────────────────────────
DB_USER="root"
DB_PASS="yourpassword"        # change this to your MySQL root password
DB_NAME="robot_fleet"
LOG_FILE="$(dirname "$0")/../logs/health.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# ── Helper: log a message ─────────────────────────────────────
log() {
    echo "[$TIMESTAMP] $1" >> "$LOG_FILE"
}

log "──────────────────────────────────────────"
log "Health check started"

# ── 1. Check MySQL is running ─────────────────────────────────
if ! systemctl is-active --quiet mysql; then
    log "CRITICAL: MySQL service is not running"
    exit 1
fi

# ── 2. Check for offline robots ───────────────────────────────
OFFLINE=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -se \
    "SELECT COUNT(*) FROM robots WHERE status='offline';" 2>/dev/null)

if [ "$OFFLINE" -gt 0 ]; then
    log "CRITICAL: $OFFLINE robot(s) are OFFLINE"
    # Log which robots are offline
    mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -se \
        "SELECT CONCAT('  → ', name, ' | battery: ', battery, '% | location: ', location)
         FROM robots WHERE status='offline';" 2>/dev/null \
    | while read -r line; do
        log "$line"
    done
else
    log "OK: No offline robots"
fi

# ── 3. Check for error state robots ──────────────────────────
ERROR=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -se \
    "SELECT COUNT(*) FROM robots WHERE status='error';" 2>/dev/null)

if [ "$ERROR" -gt 0 ]; then
    log "WARNING: $ERROR robot(s) in ERROR state"
    mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -se \
        "SELECT CONCAT('  → ', name, ' | battery: ', battery, '% | location: ', location)
         FROM robots WHERE status='error';" 2>/dev/null \
    | while read -r line; do
        log "$line"
    done
else
    log "OK: No robots in error state"
fi

# ── 4. Check for low battery robots ──────────────────────────
LOW_BAT=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -se \
    "SELECT COUNT(*) FROM robots WHERE battery < 20;" 2>/dev/null)

if [ "$LOW_BAT" -gt 0 ]; then
    log "WARNING: $LOW_BAT robot(s) have battery below 20%"
else
    log "OK: All robots have sufficient battery"
fi

# ── 5. Check for unresolved critical incidents ────────────────
CRITICAL=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -se \
    "SELECT COUNT(*) FROM incidents
     WHERE severity='critical' AND resolved_at IS NULL;" 2>/dev/null)

if [ "$CRITICAL" -gt 0 ]; then
    log "CRITICAL: $CRITICAL unresolved critical incident(s) open"
else
    log "OK: No unresolved critical incidents"
fi

# ── 6. Overall fleet summary ──────────────────────────────────
SUMMARY=$(mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -se \
    "SELECT CONCAT(
        'Fleet → active:', SUM(status='active'),
        ' idle:', SUM(status='idle'),
        ' offline:', SUM(status='offline'),
        ' error:', SUM(status='error')
     ) FROM robots;" 2>/dev/null)

log "SUMMARY: $SUMMARY"
log "Health check complete"