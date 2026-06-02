#!/bin/bash

# ── Config ────────────────────────────────────────────────────
DB_USER="root"
DB_PASS="yourpassword"        # change this to your MySQL root password
DB_NAME="robot_fleet"
BACKUP_DIR="$(dirname "$0")/../logs"
DATE=$(date '+%Y-%m-%d_%H-%M-%S')
DUMP_FILE="$BACKUP_DIR/backup_${DATE}.sql"
CSV_DIR="$BACKUP_DIR/csv_${DATE}"
LOG_FILE="$BACKUP_DIR/health.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

mkdir -p "$CSV_DIR"

log() {
    echo "[$TIMESTAMP] [BACKUP] $1" >> "$LOG_FILE"
    echo "  $1"
}

echo "============================================"
echo "  ROC-Sim Backup — $DATE"
echo "============================================"

# ── 1. Full SQL dump ──────────────────────────────────────────
log "Starting mysqldump..."
mysqldump -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" > "$DUMP_FILE" 2>/dev/null

if [ $? -eq 0 ]; then
    SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
    log "SQL dump saved: backup_${DATE}.sql ($SIZE)"
else
    log "ERROR: mysqldump failed"
    exit 1
fi

# ── 2. Export each table to CSV ───────────────────────────────
TABLES=("robots" "missions" "incidents" "metrics")

for TABLE in "${TABLES[@]}"; do
    CSV_FILE="$CSV_DIR/${TABLE}.csv"
    mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" -se \
        "SELECT * FROM $TABLE INTO OUTFILE '/tmp/roc_${TABLE}_export.csv'
         FIELDS TERMINATED BY ','
         ENCLOSED BY '\"'
         LINES TERMINATED BY '\n';" 2>/dev/null

    if [ -f "/tmp/roc_${TABLE}_export.csv" ]; then
        mv "/tmp/roc_${TABLE}_export.csv" "$CSV_FILE"
        ROWS=$(wc -l < "$CSV_FILE")
        log "CSV exported: ${TABLE}.csv ($ROWS rows)"
    else
        # Fallback: use mysql client to dump
        mysql -u"$DB_USER" -p"$DB_PASS" "$DB_NAME" \
            -e "SELECT * FROM $TABLE;" 2>/dev/null \
            | sed 's/\t/,/g' > "$CSV_FILE"
        log "CSV exported (fallback): ${TABLE}.csv"
    fi
done

# ── 3. Remove backups older than 7 days ───────────────────────
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +7 -delete
find "$BACKUP_DIR" -name "csv_*" -type d -mtime +7 \
    -exec rm -rf {} + 2>/dev/null

log "Old backups cleaned (>7 days)"

# ── 4. Final summary ──────────────────────────────────────────
log "Backup complete — files in logs/csv_${DATE}/"
echo ""
echo "  Done. Files saved to: logs/csv_${DATE}/"
echo "============================================"