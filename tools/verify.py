"""Independent verification of the gpuqos findings, sharing no code with src or
analyze.py. Re-reads results/runs.jsonl and re-derives every prediction with its own
arithmetic:

  P1  gpu_only_besteffort: the GPU-only pod is BestEffort with oom_score_adj 1000,
      identical to a bare pod -- the GPU contributes nothing to QoS.
  P2  memory_lifts_to_burstable: adding memory makes it Burstable with
      -997 < oom_score_adj < 1000.
  P3  full_reservation_guaranteed: cpu+memory req==lim makes it Guaranteed, oom -997.
  P4  ordering: BestEffort(1000) > Burstable > Guaranteed(-997); the GPU-only pod is
      the maximum (first OOM victim).

Exit non-zero on mismatch.
"""
from __future__ import annotations

import json
import sys


def main() -> int:
    r = {x["scenario"]: x for x in
         (json.loads(line) for line in open("results/runs.jsonl") if line.strip())}
    ok = True

    p = r["gpu_only_besteffort"]
    g, b = p["gpu_only"], p["bare"]
    p1 = (g["qosClass"] == "BestEffort" and g["oom_score_adj"] == 1000
          and g["qosClass"] == b["qosClass"] and g["oom_score_adj"] == b["oom_score_adj"])
    print(f"  [P1] gpu_only={g['qosClass']}/{g['oom_score_adj']} == "
          f"bare={b['qosClass']}/{b['oom_score_adj']} (GPU invisible to QoS) = {p1}")
    ok = ok and p1

    p2 = r["memory_lifts_to_burstable"]
    b2 = int(p2["oom_score_adj"])
    p2ok = p2["qosClass"] == "Burstable" and -997 < b2 < 1000
    print(f"  [P2] {p2['qosClass']}/{b2} (Burstable, -997 < oom < 1000) = {p2ok}")
    ok = ok and p2ok

    p3 = r["full_reservation_guaranteed"]
    p3ok = p3["qosClass"] == "Guaranteed" and int(p3["oom_score_adj"]) == -997
    print(f"  [P3] {p3['qosClass']}/{p3['oom_score_adj']} (Guaranteed, -997) = {p3ok}")
    ok = ok and p3ok

    p4 = r["ordering"]
    o = p4["oom_by_class"]
    seq = [int(o["besteffort"]), int(o["burstable"]), int(o["guaranteed"])]
    descending = all(a > b_ for a, b_ in zip(seq, seq[1:]))
    victim = max(o, key=lambda k: int(o[k]))
    p4ok = descending and victim == "besteffort" and seq[0] == 1000 and seq[2] == -997
    print(f"  [P4] {seq} descending={descending} first_victim={victim} = {p4ok}")
    ok = ok and p4ok

    if ok:
        print("VERIFY OK: a GPU-only pod is BestEffort with oom_score_adj 1000, identical to a "
              "pod requesting nothing (the GPU contributes nothing to QoS); adding memory lifts "
              "it to Burstable and cpu+memory req==lim to Guaranteed (-997); the three are "
              "strictly ordered so the GPU-only pod has the maximum oom_score_adj and is the "
              "kernel's first OOM victim despite being the only one holding a GPU - recomputed "
              "independently.")
        return 0
    print("VERIFY FAILED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
