# gpuqos

**A pod that requests only a GPU is BestEffort QoS -- the kernel's first OOM victim
(oom_score_adj 1000) -- because Kubernetes computes QoS from CPU and memory alone.**

Both mechanisms that reclaim memory rank pods by QoS class -- the kubelet eviction
manager (which evicts BestEffort first under node MemoryPressure) and, below it, the
Linux OOM killer (which the kubelet configures via `oom_score_adj`). QoS is computed
from CPU and memory requests/limits ONLY. A GPU is an extended resource, so it does not
count -- a pod that asks for a GPU but no CPU or memory is classified BestEffort,
exactly as if it had requested nothing. This study drives a real single-node cluster
(minikube) and reads two independent signals per pod -- the API `status.qosClass` and
the kernel `oom_score_adj` from `/proc/1/oom_score_adj` -- to show that the scarce-GPU
holder is the process both paths kill first (they agree; BestEffort is worst in each).

## The GPU is a fake integer resource (disclosed)

GPUs here are not real. The node advertises an integer extended resource
`example.com/gpu` by patching its status; pods run `busybox sleep` (so
`oom_score_adj` is readable) and do no GPU compute. This is deliberate and honest:
**QoS classification treats an extended resource identically to `nvidia.com/gpu`** --
neither contributes to QoS. No GPU compute is measured or claimed; the findings are
exact API and kernel values.

## Findings (fake GPU node)

| # | Scenario | qosClass | oom_score_adj |
|---|----------|----------|---------------|
| P1 | Pod requests only `example.com/gpu` | **BestEffort** | **1000** |
| P1 | Pod requests nothing at all (control) | BestEffort | 1000 |
| P2 | GPU + a memory request | **Burstable** | 999 (`-997 < x < 1000`) |
| P3 | GPU + cpu & memory, requests == limits | **Guaranteed** | **-997** |
| P4 | Ordering | BestEffort **>** Burstable **>** Guaranteed | 1000 > 999 > -997 |

**The headline (P4):** the GPU-only pod dies first. Its `oom_score_adj` of 1000 is the
maximum the kernel assigns, so under memory pressure it is the first process OOM-killed
-- even though it is the only pod holding a GPU. The GPU request is invisible to QoS
(P1: identical to a pod requesting nothing). The only way to protect a GPU workload is
to give it CPU and memory requests: a memory request alone lifts it to Burstable (P2),
and cpu+memory with requests == limits makes it Guaranteed with `oom_score_adj` -997
(P3), the most protected tier. A GPU-heavy pod with no CPU/memory reservation is a
footgun -- scarce hardware on the shortest leash.

## Reproduce

Requires a running minikube cluster and `kubectl` pointed at it.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python tools/run_bench.py     # drives the cluster, writes results/runs.jsonl
./reproduce.sh                          # analyze + independent verify from the recorded run
```

`tools/run_bench.py` patches the node's GPU capacity, creates the pods, and records
each pod's `status.qosClass` and its kernel `oom_score_adj` (via `kubectl exec cat
/proc/1/oom_score_adj`). `tools/verify.py` re-derives every prediction from the
recorded values with its own arithmetic (it shares no code with `src/` or
`analyze.py`) and exits non-zero on any mismatch.

## Note on the exact numbers

BestEffort (1000) and Guaranteed (-997) are fixed kernel constants. The Burstable value
follows the documented formula `1000 - 1000 * memoryRequest / nodeAllocatableMemory`,
which the kubelet then clamps to `[3, 999]` (so Burstable is always strictly below
BestEffort). For a small memory request the raw formula rounds to 1000 and the clamp
pins it to 999 -- which is why P4's ordering can never flip on any node. The study
asserts the strict ordering (`-997 < Burstable < 1000`), not the exact 999.

## Layout

- `PREREG.md` -- predictions, committed before the run.
- `src/gpuqos.py` -- pure helpers (the QoS rule over cpu/memory, contributes-to-QoS,
  strict ordering, OOM-victim selection).
- `tools/run_bench.py` -- drives the real cluster, records `results/runs.jsonl`.
- `tools/analyze.py` -- emits the frontier.
- `tools/verify.py` -- independent recompute of all four predictions.
- `tests/` -- unit tests for the pure helpers.
- `scripts/gate.sh` -- ruff, mypy `--strict`, pytest, ASCII, leak scan, verify.
- `REVIEW.md` -- pre-ship review notes.

## License

MIT.
