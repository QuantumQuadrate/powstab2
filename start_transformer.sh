#!/bin/bash
nohup python testMatrix.py &
tail -f nohup.out
