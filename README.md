# powstab2
Improved Raspberry Pi based PID controller

## Installation
```bash
sudo -H pip install wiringpi
sudo -H pip install git+https://github.com/QuantumQuadrate/ivPID
sudo -H pip install git+https://github.com/QuantumQuadrate/Origin.git
sudo -H pip install git+https://github.com/QuantumQuadrate/k10cr1.git
cd ~ ; git clone --recurse-submodules https://github.com/QuantumQuadrate/powstab2.git ; cd powstab2
ln -s <YOUR CONFIG>.cfg config.cfg
wget https://raw.githubusercontent.com/QuantumQuadrate/Origin/master/config/origin-server.cfg
```

Build the BCM2835 (processor) library and ADC/DAC interface scripts

```bash
cd Downloads
wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.55.tar.gz
tar -xvf bcm2835-1.55.tar.gz ; cd bcm2835-1.55/
./configure ; make ; sudo make install
cd powstab2/ads1256 ; make
cd ../dac8532 ; make
```

## Run

```bash
cd ~/powstab2
```

Run with a remote data source through the origin server (recommended)
```bash
nohup sudo ./main_origin.py &
```
or the local ADC based system (be aware of ~15 ms trigger latency on reads):
```bash
nohup sudo ./main.py &
```

The script runs in the background and produces a log at nohup.out.
You can now logout and it will continue to run.

A convenience script `start.sh` is included which runs the above command and then `tail -f pid.out` or `tail -f nohup.out` to watch the logs until you have verified correct operation.
When finished monitoring just `Ctrl-C` out and exit, the server will still be running.

To kill the process run
```bash
$ ps -fA | grep python
> root      1483  1478  0 16:19 pts/0    00:00:00 /usr/bin/python ./main_origin.py
> root      1488  1483  1 16:19 pts/0    00:00:03 /usr/bin/python ./main_origin.py
> pi        1499  1089  0 16:23 pts/0    00:00:00 grep --color=auto python
```
You need to kill the parent process, which is almost always the lowest process id number (1483 here).
Then kill the parent process which will shutdown the child as well.
```bash
$ sudo kill 1483
$ ps -fA | grep python
> pi        1620  1089  0 16:26 pts/0    00:00:00 grep --color=auto python
```
