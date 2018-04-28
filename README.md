# powstab2
Improved Raspberry Pi based PID controller

## Installation
```bash
sudo -H pip install wiringpi
sudo -H pip install git+https://github.com/QuantumQuadrate/ivPID
sudo -H pip install git+https://github.com/QuantumQuadrate/Origin.git
sudo -H pip install git+https://github.com/QuantumQuadrate/k10cr1.git
cd ~ ; git clone --recurse-submodules https://github.com/QuantumQuadrate/powstab2.git
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

A convenience script `start.sh` is included which runs the above command and then `tail -f nohup.out` to watch the logs until you have verified correct operation.
When finished monitoring just `Ctrl-C` out and exit, the server will still be running.
