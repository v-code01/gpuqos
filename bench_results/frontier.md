# gpuqos frontier (regenerate with tools/analyze.py)
#
# QoS class and kernel oom_score_adj per pod on a fake-GPU node. Exact facts.

gpu_only_besteffort gpu_only BestEffort/1000 bare BestEffort/1000 same_as_bare True
memory_lifts_to_burstable Burstable/999
full_reservation_guaranteed Guaranteed/-997
ordering oom {'besteffort': 1000, 'burstable': 999, 'guaranteed': -997} descending True first_victim besteffort
