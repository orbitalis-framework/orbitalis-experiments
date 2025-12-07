import yappi
import tracemalloc

def start_profiling(t: str):
    yappi.set_clock_type(t)
    yappi.start()
    tracemalloc.start()

def stop_profiling(t: str, output_path: str):
    yappi.stop()
    stats = yappi.get_func_stats()
    stats.save(output_path + f"_profile_{t}.pstat", type="pstat")

    snapshot = tracemalloc.take_snapshot()
    snapshot.dump(output_path + f"_tracemalloc.dat")
