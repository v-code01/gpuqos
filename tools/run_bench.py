"""Drive a real Kubernetes cluster to show a GPU-only pod is BestEffort QoS with the
maximum kernel oom_score_adj (the first OOM victim under memory pressure), because
extended resources do not count toward QoS. Advertises a fake integer GPU and records
two independent signals per pod: the API qosClass and the kernel oom_score_adj from
/proc/1/oom_score_adj. Writes results/runs.jsonl.

kubectl uses the current context/namespace; nothing operating-environment-specific
is in this file.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import gpuqos as q  # noqa: E402

GPU = "example.com/gpu"
NODE = "minikube"
G = 4
ROOT = Path(__file__).resolve().parent.parent


def kubectl(args: list[str], stdin: str | None = None, timeout: int = 60,
            check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["kubectl", *args], input=stdin, capture_output=True,
                          text=True, timeout=timeout, check=check)


def pod_yaml(name: str, resources: str) -> str:
    return (
        f"apiVersion: v1\nkind: Pod\nmetadata:\n  name: {name}\n  labels: {{app: qos}}\n"
        f"spec:\n  containers:\n  - name: c\n    image: busybox:1.36\n"
        f"    command: [\"sleep\", \"3600\"]\n    resources:\n{resources}")


def phase(name: str) -> str:
    p = kubectl(["get", "pod", name, "-o", "jsonpath={.status.phase}"], check=False)
    return p.stdout.strip() if p.returncode == 0 else "Gone"


def wait_running(name: str, timeout: int = 40) -> None:
    for _ in range(timeout):
        if phase(name) == "Running":
            return
        time.sleep(1)
    print(f"ERROR: {name} did not reach Running", file=sys.stderr)
    raise SystemExit(1)


def qos_of(name: str) -> str:
    return kubectl(["get", "pod", name, "-o", "jsonpath={.status.qosClass}"]).stdout.strip()


def oom_of(name: str) -> int:
    out = kubectl(["exec", name, "--", "cat", "/proc/1/oom_score_adj"]).stdout.strip()
    return int(out)


def make(name: str, resources: str) -> dict[str, Any]:
    kubectl(["create", "-f", "-"], stdin=pod_yaml(name, resources))
    wait_running(name)
    return {"name": name, "qosClass": qos_of(name), "oom_score_adj": oom_of(name)}


def clean() -> None:
    kubectl(["delete", "pods", "-l", "app=qos", "--wait=true", "--timeout=60s"],
            timeout=90, check=False)
    for _ in range(30):
        got = kubectl(["get", "pods", "-l", "app=qos", "-o",
                       "jsonpath={.items[*].metadata.name}"]).stdout.strip()
        if not got:
            break
        time.sleep(1)


# Resource stanzas (6-space indented under `resources:`).
GPU_ONLY = (f"      requests: {{{GPU}: \"1\"}}\n      limits: {{{GPU}: \"1\"}}\n")
BARE = "      {}\n"
GPU_MEM = (f"      requests: {{{GPU}: \"1\", memory: \"64Mi\"}}\n"
           f"      limits: {{{GPU}: \"1\"}}\n")
GPU_FULL = (f"      requests: {{{GPU}: \"1\", cpu: \"100m\", memory: \"64Mi\"}}\n"
            f"      limits: {{{GPU}: \"1\", cpu: \"100m\", memory: \"64Mi\"}}\n")


def main() -> int:
    kubectl(["patch", "node", NODE, "--subresource=status", "--type=json",
             "-p", f'[{{"op":"add","path":"/status/capacity/example.com~1gpu","value":"{G}"}}]'])
    rows: list[dict[str, Any]] = []

    # --- P1: GPU-only is BestEffort, same as a bare pod ---
    clean()
    gpu_only = make("gpu-only", GPU_ONLY)
    bare = make("bare", BARE)
    rows.append({"scenario": "gpu_only_besteffort", "gpu_only": gpu_only, "bare": bare,
                 "same_as_bare": gpu_only["qosClass"] == bare["qosClass"]
                 and gpu_only["oom_score_adj"] == bare["oom_score_adj"]})
    print(f"  P1 gpu_only_besteffort: gpu_only={gpu_only['qosClass']}/"
          f"{gpu_only['oom_score_adj']} bare={bare['qosClass']}/{bare['oom_score_adj']}")
    clean()

    # --- P2: memory lifts to Burstable ---
    burst = make("gpu-mem", GPU_MEM)
    rows.append({"scenario": "memory_lifts_to_burstable", **burst})
    print(f"  P2 memory_lifts_to_burstable: {burst['qosClass']}/{burst['oom_score_adj']}")
    clean()

    # --- P3: full reservation is Guaranteed ---
    guar = make("gpu-full", GPU_FULL)
    rows.append({"scenario": "full_reservation_guaranteed", **guar})
    print(f"  P3 full_reservation_guaranteed: {guar['qosClass']}/{guar['oom_score_adj']}")
    clean()

    # --- P4: ordering ---
    oom = {"besteffort": gpu_only["oom_score_adj"], "burstable": burst["oom_score_adj"],
           "guaranteed": guar["oom_score_adj"]}
    rows.append({"scenario": "ordering", "oom_by_class": oom,
                 "descending": q.ordered_desc([oom["besteffort"], oom["burstable"],
                                               oom["guaranteed"]]),
                 "first_victim": q.first_oom_victim(oom)})
    print(f"  P4 ordering: {oom} descending={rows[-1]['descending']} "
          f"first_victim={rows[-1]['first_victim']}")

    out = ROOT / "results" / "runs.jsonl"
    with open(out, "w") as file:
        for row in rows:
            file.write(json.dumps(row) + "\n")
    print(f"wrote {len(rows)} rows -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
