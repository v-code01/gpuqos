# Pre-ship review: gpuqos

Reviewed against PREREG.md and the factory rigor bar before publish.

## Findings (all held)

- **P1** gpu_only_besteffort: a pod requesting only `example.com/gpu` is BestEffort
  with oom_score_adj 1000, identical to a bare pod requesting nothing. The GPU request
  contributes nothing to QoS classification.
- **P2** memory_lifts_to_burstable: adding a memory request makes the pod Burstable
  with oom_score_adj 999, strictly inside (-997, 1000).
- **P3** full_reservation_guaranteed: cpu + memory with requests == limits makes the
  pod Guaranteed with oom_score_adj -997.
- **P4** ordering (headline): 1000 > 999 > -997, strictly descending; the GPU-only pod
  has the maximum oom_score_adj, so it is the kernel's first OOM victim under memory
  pressure -- despite being the only pod holding a GPU.

## Two independent signals

- The QoS class is read from the API (`status.qosClass`), and the oom_score_adj is read
  from the kernel (`/proc/1/oom_score_adj` via `kubectl exec`). They agree
  (BestEffort<->1000, Burstable<->999, Guaranteed<->-997), so the result is not an
  artifact of one accounting path. The oom_score_adj is the actual value the kernel
  uses to choose an OOM victim, so "dies first" is measured at the mechanism, not
  inferred.
- No memory pressure is induced (which would be flaky); the study reads the kernel's
  pre-assigned oom_score_adj, which is what determines eviction/OOM order. This is
  disclosed: the eviction consequence follows from the measured oom_score_adj plus
  documented kernel OOM policy (highest oom_score_adj first).

## Honesty / disclosure

- The GPU is a fake integer extended resource (node-status patch, busybox/sleep pods,
  no GPU compute). Disclosed in README and PREREG. QoS treats an extended resource
  identically to `nvidia.com/gpu`. No GPU compute is measured or claimed.
- The Burstable oom_score_adj (999) is node-memory-dependent per the documented
  formula; the study asserts the strict ordering/bound, not the exact 999, and says so
  in README and PREREG. BestEffort (1000) and Guaranteed (-997) are fixed constants.
- All results are exact API/kernel values, not timings -- deterministic.

## Verification

- `tools/verify.py` shares no code with `src/` or `analyze.py`; it re-reads
  `results/runs.jsonl` and re-derives every prediction (BestEffort==bare, Burstable
  bound, Guaranteed==-997, strict ordering, max-oom victim) with its own arithmetic.
  Exits non-zero on mismatch. VERIFY OK.
- Gate green: ruff, mypy --strict, pytest (8), pure-ASCII, no env leak, verify.

## Verdict

SHIP. All four pre-registered predictions held; the headline (P4, a GPU-only pod is
BestEffort with the maximum oom_score_adj, so the scarce-GPU holder is the first OOM
victim) is a clean, deterministic result confirmed by two independent signals.
