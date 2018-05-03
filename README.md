# Software Benchmarking Script
A simple method for launching a process and collecting system resource utilisation statistics.

## Usage
1. Clone the repository to your machine
```git clone https://github.com/jakeb1996/SBS```
2. Open your CLI and navigate to the root directory of the repository.
3. Run the script using the following command
```python sbs.py -c <command> -o <data-output-file> -s <polling-interval-secs> -l <tailable-y-n>```
Command arguments include:
`c` The command to run. eg: `notepad.exe`
`o` Filename for saving the data to eg: `output.csv`
`s` The polling interval for checking utilisation of system resources, in seconds. eg: `1`
`l` Toggle whether the data output file is tailable (y/n). eg: `y` ie: `tail -f output.csv.log`

## Output
Two files are generated:
1. System resource utilisation CSV which includes a header row and:
1.1 Time of recording
1.2 Number of threads created by process
1.3 CPU utilisation as percentage. Values over 100% indicate utilisation of multiple cores.
1.4 Resident Set Size memory usage (physical memory usage)
1.5 Virtual Memory Size (phy+vir memory)
1.6 IO read count
1.7 IO read bytes
1.8 IO write count
1.9 IO write bytes
1.10 Number of child processes
2. A log file describing:
2.1 Launch time
2.2 Launch parameters
2.3 Debug info (when appropriate)
2.4 Clean-up process

## Dependencies
SBS depends on the `psutil` library available via pip. 
`pip install psutil`
Pip: <https://pypi.org/project/psutil/>
Documentation: <https://psutil.readthedocs.io>