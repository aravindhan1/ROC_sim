#!/bin/bash

# ── Config ────────────────────────────────────────────────────
LOG_FILE="$(dirname "$0")/../logs/health.log"
LINES=${1:-50}    # how many recent lines to scan (default 50)

echo "============================================"
echo "  ROC-Sim Log Monitor"
echo "  Scanning: $LOG_FILE"
echo "  Last $LINES lines"
echo "============================================"
echo ""

# ── Check log file exists ─────────────────────────────────────
if [ ! -f "$LOG_FILE" ]; then
    echo "  No log file found at: $LOG_FILE"
    echo "  Run health_check.sh first to generate logs."
    exit 1
fi

# ── Show all CRITICAL entries ─────────────────────────────────
echo "── CRITICAL ALERTS ──────────────────────────"
CRITICAL_COUNT=$(tail -n "$LINES" "$LOG_FILE" | grep -c "CRITICAL")
if [ "$CRITICAL_COUNT" -gt 0 ]; then
    tail -n "$LINES" "$LOG_FILE" | grep "CRITICAL"
else
    echo "  None found in last $LINES lines."
fi

echo ""

# ── Show all WARNING entries ──────────────────────────────────
echo "── WARNINGS ─────────────────────────────────"
WARN_COUNT=$(tail -n "$LINES" "$LOG_FILE" | grep -c "WARNING")
if [ "$WARN_COUNT" -gt 0 ]; then
    tail -n "$LINES" "$LOG_FILE" | grep "WARNING"
else
    echo "  None found in last $LINES lines."
fi

echo ""

# ── Show recent OK entries ────────────────────────────────────
echo "── RECENT OK STATUS ────────────────────────"
tail -n "$LINES" "$LOG_FILE" | grep "OK" | tail -5

echo ""

# ── Show last 5 SUMMARY lines ─────────────────────────────────
echo "── FLEET SUMMARY (last 5 checks) ───────────"
grep "SUMMARY" "$LOG_FILE" | tail -5

echo ""

# ── Live watch mode ───────────────────────────────────────────
echo "──────────────────────────────────────────"
echo "  Tip: run with --watch to follow live:"
echo "  tail -f $LOG_FILE | grep --line-buffered 'CRITICAL\|WARNING'"
echo "──────────────────────────────────────────"