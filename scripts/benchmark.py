"""
End-to-end latency + FPS benchmark.
Runs inference on random frames and reports timing statistics.
Run: python benchmark.py
"""
import sys, os, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from inference import inspector

WARMUP_RUNS = 10
BENCH_RUNS  = 100
IMG_H, IMG_W = 720, 1280   # simulate webcam frame

def benchmark():
    print(f"[Benchmark] Warming up ({WARMUP_RUNS} runs)...")
    for _ in range(WARMUP_RUNS):
        frame = np.random.randint(0, 255, (IMG_H, IMG_W, 3), dtype=np.uint8)
        inspector.run(frame)

    print(f"[Benchmark] Running {BENCH_RUNS} inference passes...")
    latencies = []
    for i in range(BENCH_RUNS):
        frame = np.random.randint(0, 255, (IMG_H, IMG_W, 3), dtype=np.uint8)
        t0    = time.perf_counter()
        inspector.run(frame)
        latencies.append((time.perf_counter() - t0) * 1000)
        if (i+1) % 20 == 0:
            print(f"  {i+1}/{BENCH_RUNS} done")

    lat = np.array(latencies)
    print("\n====== Benchmark Results ======")
    print(f"  Avg latency : {lat.mean():.2f} ms")
    print(f"  Min latency : {lat.min():.2f} ms")
    print(f"  Max latency : {lat.max():.2f} ms")
    print(f"  P95 latency : {np.percentile(lat,95):.2f} ms")
    print(f"  P99 latency : {np.percentile(lat,99):.2f} ms")
    print(f"  Avg FPS     : {1000/lat.mean():.1f}")
    print(f"  Min FPS     : {1000/lat.max():.1f}")

if __name__ == "__main__":
    benchmark()