# Pre-registration: gpuqos

Committed to git BEFORE the benchmark is run. Not edited afterward.

## What is measured

On a real single-node Kubernetes cluster (minikube), GPUs are a fake integer extended
resource `example.com/gpu` advertised by patching the node status. Pods run a
`busybox sleep` container so their kernel `oom_score_adj` can be read. The study
measures how a GPU-requesting pod is classified for eviction: Kubernetes QoS classes
are computed from CPU and MEMORY requests/limits ONLY -- extended resources like a GPU
do not count -- so a pod that requests only a GPU is BestEffort, which the kernel
tags with the maximum `oom_score_adj` (1000), making it the first process killed under
memory pressure despite holding scarce hardware.

Two independent signals are recorded for each pod: the API `status.qosClass`, and the
kernel `oom_score_adj` read from `/proc/1/oom_score_adj` inside the container. Four
scenarios, each exact:

- **P1 gpu_only_besteffort.** A pod requesting only `example.com/gpu` (no cpu/memory),
  compared with a bare pod requesting nothing. Record qosClass and oom_score_adj of
  both.
- **P2 memory_lifts_to_burstable.** A pod requesting the GPU plus a memory request.
  Record qosClass and oom_score_adj.
- **P3 full_reservation_guaranteed.** A pod requesting the GPU plus cpu and memory
  with requests == limits. Record qosClass and oom_score_adj.
- **P4 ordering.** Compare the three oom_score_adj values.

## Predictions

**P1 - a GPU is invisible to QoS.** The GPU-only pod is BestEffort with
oom_score_adj = 1000, identical to the bare pod requesting nothing - the GPU request
contributes nothing to QoS. *Falsifier:* the GPU-only pod is not BestEffort, or its
oom_score_adj differs from the bare pod's.

**P2 - memory lifts to Burstable.** Adding a memory request makes the pod Burstable
with oom_score_adj strictly between Guaranteed and BestEffort (-997 < x < 1000).
*Falsifier:* it is not Burstable, or its oom_score_adj is outside that open interval.

**P3 - full reservation is Guaranteed.** Adding cpu and memory with requests == limits
makes the pod Guaranteed with oom_score_adj = -997. *Falsifier:* it is not Guaranteed,
or oom_score_adj != -997.

**P4 - the GPU-only pod dies first (headline).** The oom_score_adj values are strictly
ordered BestEffort (1000) > Burstable > Guaranteed (-997), so the GPU-only pod has the
maximum oom_score_adj and is the kernel's first OOM victim under memory pressure -
even though it, and only it, holds a GPU. *Falsifier:* the ordering does not hold, or
the GPU-only pod is not the maximum.

## Commitment

P4 (a GPU-only pod is BestEffort with the maximum oom_score_adj, so the scarce-GPU
holder is the first to be OOM-killed; adding cpu/memory is the only way to protect it)
is the headline; P1 shows the GPU is invisible to QoS, P2/P3 the lifts. The exact
Burstable oom_score_adj depends on the node's memory size (documented kernel formula),
so P2 is asserted as an ordering/bound, not an exact number; BestEffort (1000) and
Guaranteed (-997) are fixed. The fake GPU is an integer extended resource; QoS
classification treats it identically to `nvidia.com/gpu`. Results are reported as-is,
including any falsified prediction.
