"""Pure helpers for the gpuqos study: the Kubernetes QoS-class rule (computed from CPU
and memory only, ignoring extended resources), which resources contribute to QoS,
strict-descending ordering, and OOM-victim selection. No I/O."""
from __future__ import annotations

# Only these resources are considered for QoS classification. Extended resources
# (example.com/gpu, nvidia.com/gpu, ...) are deliberately absent.
QOS_RESOURCES = ("cpu", "memory")


def qos_class(cpu_req: int, cpu_lim: int, mem_req: int, mem_lim: int) -> str:
    """QoS class of a single-container pod from its cpu/memory requests and limits.

    Guaranteed: cpu and memory both set with request == limit (> 0).
    BestEffort: no cpu or memory request/limit set at all.
    Burstable:  anything in between.
    (Extended resources such as a GPU are not inputs -- they do not affect QoS.)"""
    any_set = any(v > 0 for v in (cpu_req, cpu_lim, mem_req, mem_lim))
    if not any_set:
        return "BestEffort"
    guaranteed = (cpu_req == cpu_lim > 0) and (mem_req == mem_lim > 0)
    return "Guaranteed" if guaranteed else "Burstable"


def contributes_to_qos(resource: str) -> bool:
    """Whether a resource name is counted in QoS classification."""
    return resource in QOS_RESOURCES


def ordered_desc(values: list[int]) -> bool:
    """Whether values are strictly decreasing."""
    return all(a > b for a, b in zip(values, values[1:]))


def first_oom_victim(oom_by_name: dict[str, int]) -> str:
    """The pod name with the maximum oom_score_adj (the kernel's first OOM target)."""
    return max(oom_by_name, key=lambda name: oom_by_name[name])
