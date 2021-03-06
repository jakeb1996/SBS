# Software Benchmarking Script
A simple method for launching a process and collecting system resource utilisation statistics.

## Contents
`sbs.py` is used to execute a command and monitor system resources used by the opened process

`plotter.py` is used to plot the output data generated by `sbs.py`

`stats.py` is used to generate statistics on the data generated by `sbs.py`

## Usage
1. Clone the repository to your machine

```git clone https://github.com/jakeb1996/SBS```

2. Open your CLI and navigate to the root directory of the repository.

3. (optional) Add to Windows context menu if you wish to quickly analyse SBS output with `plotter.py` and `stats.py` (otherwise just manually run these scripts). 

In Registry Editor:

* Create `HKEY_CLASSES_ROOT/*/shell/SBS Plot` and  `HKEY_CLASSES_ROOT/*/shell/SBS Plot/command`  

Set the value for `command` to `C:\python27\python.exe C:\git\SBS\plotter.py --wincntxmnu -f "%1"`  

* Create `HKEY_CLASSES_ROOT/*/shell/SBS Stats` and  `HKEY_CLASSES_ROOT/*/shell/SBS Stats/command`  

Set the value for `command` to `C:\python27\python.exe C:\git\SBS\stats.py --wincntxmnu -f "%1"`  

### sbs.py
3. To run the `sbs.py` script, use the following command:

```python sbs.py -c <command> -o <data-output-file> -s <polling-interval-secs> -l <tailable-y-n>```

Command arguments include:

* `-c` The command to run. eg: `notepad.exe`. 

* `-o` Filename for saving the data to eg: `output.csv`. 

* `-s` The polling interval for checking utilisation of system resources, in seconds. eg: `1`. 

* `-l` Toggle whether the data output file is tailable (y/n). eg: `y` ie: `tail -f output.csv.log`

### plotter.py
4. To run the `plotter.py` script, use the following command:

```python plotter.py -f <data-input-file> -t <tool-name-as-string>```

Command arguments include:

`f` The data input file (in CSV format) generated by `sbs.py` eg: `output.csv`. 

Note: if you input a path and partial filename, `plotter.py` will search for appropriate files that match (files that end with a PID, the words `aggregate` and `system`). The following files would match if `output/toolName-0001` was the value for `-f`.

```
output/toolName-0001_2424
output/toolName-0001_19
output/toolName-0001_35838
output/toolName-0001_aggregate
output/toolName-0001_system
```

`t` The name of the tool analysed by `sbs.py` eg: `"Cas-OFFinder"`

Plots are configured within the Python script. See file for details.


### stats.py
5. To run the `stats.py` script, use the following command:

```python stats.py -f <data-input-file> -t <tool-name-as-string>```

Command arguments include:

`f` The data input file (in CSV format) generated by `sbs.py` eg: `output.csv`

Note: if you input a path and partial filename, `plotter.py` will search for appropriate files that match (files that end with a PID, the words `aggregate` and `system`). The following files would match if `output/toolName-0001` was the value for `-f`.

```
output/toolName-0001_2424
output/toolName-0001_19
output/toolName-0001_35838
output/toolName-0001_aggregate
output/toolName-0001_system
```

`t` The name of the tool analysed by `sbs.py` eg: `"Cas-OFFinder"`

Statistical output is configured within the Python script. See file for details.


## Output
### sbs.py

Many files are generated by `sbs.py`:

1. The most important; a CSV-formatted file located and named according to the `-o` argument, with `_aggregate` concatenated on the end. This file is an aggregate of all system resource utilisation (consumed by the flag `-c` and its children). By default, the following is included in that file:

*Notably, some values are instantaneous (eg: CPU usage) and some are cumulative (total read operations on the disk since starting).*

**Instantaneous statistics**

```
Time of recording

Number of threads 

CPU utilisation as percentage. Values over 100% indicate utilisation of multiple cores.

Resident Set Size memory usage (physical memory usage)

Virtual Memory Size (phy+vir memory)

Number of child processes
```

**Cumulative statistics**

```
IO read count

IO read bytes

IO write count

IO write bytes
```

A log file describing:
 
- Launch time

- Launch parameters

- Debug info (when appropriate)

- Clean-up process

Example name: `output/toolName0001_aggregate`

2.	For each process launched (parent, children, grandchildren, etc.), a file with the same specification as described above is generated. This file is process specific and is not an aggregation of data.

Example name: `output/toolName0001_28529`

3.	A CSV-formatted file describing the overall utilisation of system resources. It contains very similar data to the process specific system utilisation files.

Example name: `output/toolName0001_system`

4.	A CSV-formatted file which lists the commands executed to launch each child.

Example name: `output/toolName0001_child_cmds`

5.	A CSV-formatted file which lists the start and end times of child processes. This file can be used with `plotter.py`.

Example name: `output/toolName0001_child_cmds_plot`

6.	A copy of the stdout from the `sbs.py` script. 

Example name: `output/toolName0001_stdout_log`

### plotter.py
Associated PNG files are generated for each plot. Output files are placed in the same directory as the input file.

### stats.py
A single CSV file is generated for data measurement. The output file is placed in the same directory as the input file. Currently `stats.py` generates the following:

 - Count (number of data points)
 
 - Minimum
 
 - Maximum
 
 - Median
 
 - Mean
 
 - Upper quartile
 
 - Lower quartile
 
 - Standard deviation
 
 - Start time
 
 - End time
 
 - Elapsed time

## Dependencies
SBS depends on the `psutil` library available via pip. 

`pip install psutil`

Pip: <https://pypi.org/project/psutil/>

Documentation: <https://psutil.readthedocs.io>