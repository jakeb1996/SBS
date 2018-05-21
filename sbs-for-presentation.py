import psutil, time, argparse
	
def main(cmd):
    process = psutil.Popen(cmd)

    while process.is_running():
        with process.oneshot():
            mem = process.memory_info()
            io = process.io_counters()
            
            print ','.join(map(str, 
                [time.time(),
                process.num_threads(),
                process.cpu_percent(0.1),
                mem.rss,
                mem.vms,
                io.read_count,
                io.read_bytes,
                io.write_count,
                io.write_bytes,
                len(process.children())]))
        
        time.sleep(1)
        
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description = 'Software Benchmarking Script')
    parser.add_argument('-c', help='Command to run', default=None, required=True)

    args = parser.parse_args()

    main(args.c)