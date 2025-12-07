import tracemalloc
import os
import linecache


def analyze_snapshot(filename):
    """
    Loads a tracemalloc snapshot and prints the top memory consumers.
    """
    if not os.path.exists(filename):
        print(f"Error: The file '{filename}' was not found.")
        return

    print(f"--- Loading snapshot: {filename} ---")
    
    # 1. Load the snapshot from the file
    try:
        snapshot = tracemalloc.Snapshot.load(filename)
    except Exception as e:
        print(f"Error loading snapshot: {e}")
        return

    # 2. Filter (Optional)
    # Uncomment the lines below to see only files related to your project (e.g., 'orbitalis')
    # and ignore Python internal libraries.
    # snapshot = snapshot.filter_traces((
    #     tracemalloc.Filter(inclusive=True, name_pattern="*orbitalis*"),
    # ))

    # 3. Top 10 Statistics by Line Number
    print("\n[ TOP 10 MEMORY CONSUMERS (Grouped by Line) ]")
    top_stats = snapshot.statistics('lineno')

    if not top_stats:
        print("No memory allocations found in this snapshot.")
        return

    for index, stat in enumerate(top_stats[:10], 1):
        frame = stat.traceback[0]
        size_mb = stat.size / 1024 / 1024
        print(f"#{index}: {size_mb:.2f} MiB -> {frame.filename}:{frame.lineno}")
        
        # Print the actual code line if available
        code_line = get_code_line(frame.filename, frame.lineno)
        if code_line:
            print(f"    Code: {code_line}")

    # 4. Top 3 Tracebacks (Full Call Stack)
    # This helps identify if the memory is held by a deep copy or specific function call chain.
    print("\n[ TOP 10 LARGEST ALLOCATIONS (Full Traceback) ]")
    top_tracebacks = snapshot.statistics('traceback')
    
    for index, stat in enumerate(top_tracebacks[:10], 1):
        size_mb = stat.size / 1024 / 1024
        print(f"\n#{index} Allocation: {size_mb:.2f} MiB")
        for line in stat.traceback.format():
            print(line.strip())

def get_code_line(filename, lineno):
    """Helper to safely read a specific line from a source file."""
    try:
        line = linecache.getline(filename, lineno).strip()
        return line if line else "N/A (Source not found)"
    except Exception:
        return "N/A"

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python show_tracemalloc.py <tracemalloc_snapshot_file>")
        sys.exit(1)

    analyze_snapshot(sys.argv[1])