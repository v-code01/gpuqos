import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import gpuqos as q


def test_qos_gpu_only_is_besteffort() -> None:
    # no cpu/memory set (GPU is not passed here; it does not count) -> BestEffort
    assert q.qos_class(0, 0, 0, 0) == "BestEffort"


def test_qos_memory_request_is_burstable() -> None:
    # memory request but no limit -> Burstable
    assert q.qos_class(0, 0, 64, 0) == "Burstable"


def test_qos_cpu_and_mem_req_eq_lim_is_guaranteed() -> None:
    assert q.qos_class(100, 100, 64, 64) == "Guaranteed"


def test_qos_mem_req_ne_lim_is_burstable() -> None:
    # cpu matched but memory request != limit -> Burstable, not Guaranteed
    assert q.qos_class(100, 100, 64, 128) == "Burstable"


def test_qos_only_cpu_set_is_burstable() -> None:
    assert q.qos_class(100, 100, 0, 0) == "Burstable"


def test_contributes_to_qos() -> None:
    assert q.contributes_to_qos("cpu") is True
    assert q.contributes_to_qos("memory") is True
    assert q.contributes_to_qos("example.com/gpu") is False
    assert q.contributes_to_qos("nvidia.com/gpu") is False


def test_ordered_desc() -> None:
    assert q.ordered_desc([1000, 999, -997]) is True
    assert q.ordered_desc([1000, 1000, -997]) is False
    assert q.ordered_desc([-997, 999, 1000]) is False


def test_first_oom_victim() -> None:
    assert q.first_oom_victim({"gpu": 1000, "burst": 999, "guar": -997}) == "gpu"
