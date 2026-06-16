"""自适应任务调度器 — 根据 CPU 核数调整并发度"""
import os, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

_CPU_CORES = max(2, min(os.cpu_count() or 4, 8))


def io_pool():
    return ThreadPoolExecutor(max_workers=_CPU_CORES, thread_name_prefix="radar")


def batch_run(fn, items, desc="处理中", timeout=30, pool=None):
    own_pool = pool is None
    if own_pool:
        pool = io_pool()
    results = {}
    futures = {pool.submit(fn, item): i for i, item in enumerate(items)}
    for future in as_completed(futures):
        idx = futures[future]
        try:
            results[idx] = future.result(timeout=timeout)
        except Exception:
            traceback.print_exc()
            results[idx] = None
    if own_pool:
        pool.shutdown(wait=True)
    return results
