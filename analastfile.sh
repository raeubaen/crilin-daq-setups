#!/bin/bash

folder=$(ls -1 local/rawdata | sort -V | tail -n 1)

lastfile=$(ls -1 local/rawdata/$folder | sort -V | tail -n 2 | head -n 1)

./WaveformDebugger -i local/rawdata/$folder/$lastfile

cp RawHisto.root waveform_debugger_output/WaveformDebugger_$lastfile

expect -c 'spawn -noecho root --web=off -l RawHisto.root
           send "TBrowser a;\r"
           interact'

rm RawHisto.root
