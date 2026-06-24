#!/usr/bin/python -u

import os
import sys
import re
import time
import glob
import shlex
import getopt
import subprocess

DAQ_dir = "/home/mu2e/DAQ"

RunControl_log_file = "%s/log/RunControlServer.log"%DAQ_dir

RunInfo_dir = "%s/runs"%DAQ_dir

Status = {
    "0": "CREATED",
    "1": "INITIALIZED",
    "2": "RUNNING",
    "3": "END_OK",
    "5": "INIT_ERROR",
    "6": "END_ERROR",
    "7": "UNKNOWN"
}

def execute_command(command):

    p = subprocess.Popen(shlex.split(command),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    (out,err) = p.communicate()

    return (p.returncode,out,err)

def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S",time.gmtime())

def get_next_run_from_log():

    run = {}
    with open(RunControl_log_file,'r') as rcl:
        for line in rcl:

            # Start of run pattern
            r = re.match("^.* Run number:\s+(\d+)\s*$",line)
            if r:
                new_run_nr = int(r.group(1))
                if "number" in run:
                    if new_run_nr == 0:
                        if "name" in run:
                            yield run
                        else:
                            print  "*** WARNING *** Run 0 with no name: ignoring"
                    elif new_run_nr != run["number"]:
                        yield run
                    else:
                        # If we get here, the run was started twice: just forget about the first instance
                        pass
                    #    print "*** WARNING *** Run %s was started twice"%new_run_nr
                run = { "number": new_run_nr }

            # Run name2023-04-20 13:17:36 Creating log directory ./runs/run_0000001_20230420_131736/log

            r = re.match("^.* Creating log directory .*/runs\/(\S+)\/log\s*$",line)
            if r:
                run["name"] = r.group(1)
                #print run["name"]

            # Run sor/eor comments
            r = re.match("^.* Run comment:\s+(.*)$",line)
            if r:
                if re.match("^.* End of Run comment:\s+(.*)$",line):
                    run["eor_comment"] = r.group(1)
                else:
                    run["sor_comment"] = r.group(1)

            # Run type
            r = re.match("^.* Run type:\s+(.*)$",line)
            if r: run["type"] = r.group(1)

            # Run user
            r = re.match("^.* Run crew:\s+(.*)$",line)
            if r: run["user"] = r.group(1)

            # Run create time
            r = re.match("^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) Creating Run \d+ structure in DB.*$",line)
            if r: run["create_time"] = r.group(1)

            # Run init time
            #      <2020 syntax
            r = re.match("^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) All boards completed initialization",line)
            if r: run["init_time"] = r.group(1)
            #      >=2020 syntax
            r = re.match("^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) RunControl - All subsystems initialized: DAQ run can be started.*$",line)
            if r: run["init_time"] = r.group(1)

            # Run start time
            #      Early 2018 syntax
            r = re.match("^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) Starting run$",line)
            if r: run["start_time"] = r.group(1)
            #      Final syntax
            r = re.match("^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) Enabling triggers.*$",line)
            if r: run["start_time"] = r.group(1)

            # Run stop time
            #      Early 2018 syntax
            r = re.match("^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) Stopping run$",line)
            if r: run["stop_time"] = r.group(1)
            #      Final syntax
            r = re.match("^(\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d) Disabling triggers.*$",line)
            if r: run["stop_time"] = r.group(1)

    # Return very last run in the log
    yield run

def fix_run_info(run):
    # Fix a few known problems in log file information
    #if run["name"] == "run_0000000_20190114_201456": run["user"] = ""
    #if run["name"] == "run_0000000_20181027_211827": run["user"] = ""
    #if run["name"] == "run_0000000_20181025_143612": run["user"] = ""
    #if run["name"] == "run_0000000_20181017_020807": run["user"] = ""
    #if run["name"] == "run_0_20180927_160917":       run["user"] = ""
    return run
 
def main(argv):

    for run in get_next_run_from_log():
        if ("name" in run):

            # Fix a few known problems in run information
            run = fix_run_info(run)

            print "/---------------------------------/"

            # Check if creation time can be extracted from run name
            r = re.match("^run_\d+_(\d\d\d\d)(\d\d)(\d\d)_(\d\d)(\d\d)(\d\d)$",run["name"])
            if r:
                name_time = "%s-%s-%s %s:%s:%s"%(r.group(1),r.group(2),r.group(3),r.group(4),r.group(5),r.group(6))
                if "create_time" in run:
                    if name_time != run["create_time"]:
                        print "WARNING: Name time: %s - Create time: %s - Using name time"%(name_time,run["create_time"])
                        run["create_time"] = name_time
                else:
                    print "WARNING: No Create time found - Using name time %s"%name_time
                    run["create_time"] = name_time

            # Desume run status from previous info
            if "stop_time" in run:
                run["status"] = "3"
            elif "start_time" in run:
                run["status"] = "2"
            elif "init_time" in run:
                run["status"] = "1"
            else:
                run["status"] = "5"

            # Get additional info from run cfg/log files
            run_cfg_dir = "%s/%s/cfg"%(RunInfo_dir,run["name"])
            run_log_dir = "%s/%s/log"%(RunInfo_dir,run["name"])

            merger_total_events = -1
            merger_log_file = "%s/%s_merger.log"%(run_log_dir,run["name"])
            if os.path.isfile(merger_log_file):
                with open(merger_log_file,'r') as ml:
                    for line in ml:
                        r = re.match("^DBINFO - .* - process_set_total_events (\d+)\s*$",line)
                        if r: merger_total_events = int(r.group(1))

            lvl1_total_events = -1
            lvl1_log_list = glob.glob("%s/%s_lvl1_*.log"%(run_log_dir,run["name"]))
            if lvl1_log_list:
                for lvl1_log_file in lvl1_log_list:
                    with open(lvl1_log_file,'r') as ll:
                        for line in ll:
                            r = re.match("^RootIO::Exit - Total events written: (\d+)\s*$",line)
                            if r:
                                if lvl1_total_events == -1:
                                    lvl1_total_events = int(r.group(1))
                                else:
                                    lvl1_total_events += int(r.group(1))

            if (merger_total_events != -1) and (lvl1_total_events != merger_total_events):
                print "*** WARNING *** Merger and Level1 total events differ (%d vs %d)"%(merger_total_events,lvl1_total_events)
            if lvl1_total_events != -1:
                run["total_events"] = str(lvl1_total_events)

            # Get run configuration information
            run_cfg_file = "%s/%s.cfg"%(run_cfg_dir,run["name"])
            if os.path.isfile(run_cfg_file):
                with open(run_cfg_file,'r') as rcf:
                    for line in rcf:
                        r = re.match("^setup\s+(.*)$",line)
                        if r: run["setup"] = r.group(1)
                        r = re.match("^board_list\s+(.*)$",line)
                        if r: run["board_list"] = r.group(1)

            if "name"             in run: print "Run name:",run["name"]
            if "number"           in run: print "Run number:",run["number"]
            if "user"             in run: print "Run user:",run["user"]
            if "type"             in run: print "Run type:",run["type"]
            if "setup"            in run: print "Run setup:",run["setup"]
            if "board_list"       in run: print "Board list:",run["board_list"]
            if "status"           in run: print "Run status:",run["status"],Status[run["status"]]
            if "sor_comment"      in run: print "Run SOR comment:",run["sor_comment"]
            if "eor_comment"      in run: print "Run EOR comment:",run["eor_comment"]
            if "create_time"      in run: print "Run create time:",run["create_time"]
            if "init_time"        in run: print "Run init time:",run["init_time"]
            if "start_time"       in run: print "Run start time:",run["start_time"]
            if "stop_time"        in run: print "Run stop time:",run["stop_time"]
            if "total_events"     in run: print "Run total events:",run["total_events"]
            if merger_total_events != -1: print "Merger total events:",merger_total_events
            if lvl1_total_events   != -1: print "Level1 total events:",lvl1_total_events

# Execution starts here
if __name__ == "__main__":
   main(sys.argv[1:])
