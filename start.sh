#!/bin/bash
nohup sudo ./main_origin.py &
# tail -f nohup.out
tail -f pid.log
