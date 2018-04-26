# powstab2
Improved Raspberry Pi based PID controller

## Installation
```bash
sudo -H pip install wiringpi
sudo -H pip install git+https://github.com/QuantumQuadrate/ivPID
sudo -H pip install git+https://github.com/QuantumQuadrate/Origin.git
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

Run the local ADC based system:
```bash
nohup sudo ./main.py &
```

or with a source through the origin server
```bash
nohup sudo ./main_origin.py &
```

Runs in background and produces a log at nohup.out.
You can now logout and it will continue to run.
