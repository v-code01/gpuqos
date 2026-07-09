"""Analyze results/runs.jsonl: the four gpuqos probes. Writes
bench_results/frontier.md."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load() -> dict[str, dict[str, Any]]:
    path = Path(__file__).resolve().parent.parent / "results" / "runs.jsonl"
    return {r["scenario"]: r for r in (json.loads(x) for x in open(path) if x.strip())}


def main() -> int:
    r = load()
    p1 = r["gpu_only_besteffort"]
    p2 = r["memory_lifts_to_burstable"]
    p3 = r["full_reservation_guaranteed"]
    p4 = r["ordering"]

    g = p1["gpu_only"]
    b = p1["bare"]
    lines = [
        "# gpuqos frontier (regenerate with tools/analyze.py)",
        "#",
        "# QoS class and kernel oom_score_adj per pod on a fake-GPU node. Exact facts.",
        "",
        f"gpu_only_besteffort gpu_only {g['qosClass']}/{g['oom_score_adj']} "
        f"bare {b['qosClass']}/{b['oom_score_adj']} same_as_bare {p1['same_as_bare']}",
        f"memory_lifts_to_burstable {p2['qosClass']}/{p2['oom_score_adj']}",
        f"full_reservation_guaranteed {p3['qosClass']}/{p3['oom_score_adj']}",
        f"ordering oom {p4['oom_by_class']} descending {p4['descending']} "
        f"first_victim {p4['first_victim']}",
    ]

    out = Path(__file__).resolve().parent.parent / "bench_results" / "frontier.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
