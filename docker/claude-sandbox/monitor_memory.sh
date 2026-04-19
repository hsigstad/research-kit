#!/usr/bin/env bash
# Monitor container memory usage and kill the heaviest process if above threshold.
# Uses cgroup stats (works correctly inside Docker, unlike `free`).
# Usage: monitor_memory.sh [threshold_percent] [interval_seconds]

THRESHOLD=${1:-75}
INTERVAL=${2:-10}

# Detect cgroup version and find memory limit/usage paths.
get_memory() {
    if [ -f /sys/fs/cgroup/memory.max ]; then
        # cgroup v2
        limit=$(cat /sys/fs/cgroup/memory.max)
        usage=$(cat /sys/fs/cgroup/memory.current)
    elif [ -f /sys/fs/cgroup/memory/memory.limit_in_bytes ]; then
        # cgroup v1
        limit=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
        usage=$(cat /sys/fs/cgroup/memory/memory.usage_in_bytes)
    else
        echo "[memory-monitor] Cannot read cgroup memory stats" >&2
        exit 1
    fi

    # "max" or very large value means no limit
    if [ "$limit" = "max" ] || [ "$limit" -gt 1099511627776 ] 2>/dev/null; then
        echo "0"
        return
    fi

    echo $(( usage * 100 / limit ))
}

echo "[memory-monitor] Started (threshold=${THRESHOLD}%, interval=${INTERVAL}s)"

while true; do
    pct=$(get_memory)
    if [ "$pct" -eq 0 ]; then
        sleep "$INTERVAL"
        continue
    fi

    if [ "$pct" -ge "$THRESHOLD" ]; then
        victim=$(ps aux --sort=-%mem | awk 'NR>1 && $11 !~ /claude/ && $11 !~ /node/ && $11 !~ /monitor/ {print $2; exit}')
        if [ -n "$victim" ]; then
            echo "[memory-monitor] Container at ${pct}% >= ${THRESHOLD}%. Killing PID $victim ($(ps -p $victim -o comm= 2>/dev/null))"
            kill "$victim" 2>/dev/null
        fi
    elif [ "$pct" -ge 60 ]; then
        echo "[memory-monitor] Warning: container at ${pct}%"
    fi
    sleep "$INTERVAL"
done
