import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any

LOG_PATH_DEFAULT = "logs/messages.log"
TIME_FORMAT = "%y:%m:%d:%H:%M:%S" 


def parse_ts(ts_raw: Any) -> float:
    try:
        if isinstance(ts_raw, (int, float)):
            return float(ts_raw)
        return datetime.strptime(ts_raw, TIME_FORMAT).timestamp()
    except Exception:
        return 0.0


def load_logs(path: str) -> List[Dict[str, Any]]:
    logs = []
    if not os.path.exists(path):
        return logs
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                obj["_ts"] = parse_ts(obj.get("time"))
                logs.append(obj)
            except Exception:
                continue
    logs.sort(key=lambda x: x.get("_ts", 0))
    return logs


def summarize(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(logs)
    by_perf = Counter([l.get("performative") for l in logs])
    by_sender = Counter([l.get("from") for l in logs])

    # Latency per conversation-id (dari pesan pertama ke terakhir) = makespan per percakapan
    conv_times = defaultdict(list)
    for l in logs:
        conv = l.get("conversation_id")
        conv_times[conv].append(l.get("_ts", 0))

    latencies = []
    for conv, ts_list in conv_times.items():
        if not ts_list:
            continue
        start = min(ts_list)
        end = max(ts_list)
        if end >= start:
            latencies.append(end - start)

    # Response time per conversation: dari pesan pertama ke pesan kedua (request -> response sederhana)
    response_times = []
    for conv, ts_list in conv_times.items():
        ts_list_sorted = sorted(ts_list)
        if len(ts_list_sorted) >= 2:
            response_times.append(ts_list_sorted[1] - ts_list_sorted[0])

    # Total makespan keseluruhan (global)
    all_ts = [l.get("_ts", 0) for l in logs if l.get("_ts", 0) > 0]
    total_makespan = (max(all_ts) - min(all_ts)) if len(all_ts) >= 2 else 0

    # Failure rate dan recovery time (jika ada performative == "failure")
    failures = [l for l in logs if l.get("performative") == "failure"]
    failure_rate = len(failures) / total if total > 0 else 0

    recovery_times = []
    logs_by_conv = defaultdict(list)
    for l in logs:
        logs_by_conv[l.get("conversation_id")].append(l)
    for conv, items in logs_by_conv.items():
        items_sorted = sorted(items, key=lambda x: x.get("_ts", 0))
        fail_ts = None
        for entry in items_sorted:
            if entry.get("performative") == "failure":
                fail_ts = entry.get("_ts", 0)
            elif fail_ts is not None:
                # pertama non-failure setelah failure
                rec_ts = entry.get("_ts", 0)
                if rec_ts > fail_ts:
                    recovery_times.append(rec_ts - fail_ts)
                    fail_ts = None

    # Reassign count (jika ada performative 'reassign')
    reassign_count = by_perf.get("reassign", 0)

    def stats(nums: List[float]):
        if not nums:
            return {"count": 0, "min": 0, "max": 0, "avg": 0}
        return {
            "count": len(nums),
            "min": min(nums),
            "max": max(nums),
            "avg": sum(nums) / len(nums),
        }

    summary = {
        "total_messages": total,
        "by_performative": dict(by_perf),
        "by_sender": dict(by_sender),
        "latency_per_conversation_seconds": stats(latencies),
        "response_time_seconds": stats(response_times),
        "total_makespan_seconds": total_makespan,
        "failure_count": len(failures),
        "failure_rate": failure_rate,
        "reassign_count": reassign_count,
        "recovery_time_after_failure_seconds": stats(recovery_times),
    }
    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluasi log komunikasi agen")
    parser.add_argument("--log", default=LOG_PATH_DEFAULT, help="Path file log (default logs/messages.log)")
    parser.add_argument("--output", default="logs/evaluasi.json", help="Path output ringkasan evaluasi")
    args = parser.parse_args()

    logs = load_logs(args.log)
    summary = summarize(logs)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)

    # Cetak ringkasan ke terminal
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

