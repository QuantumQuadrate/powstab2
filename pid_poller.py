import zmq
import multiprocessing
import sys
import time
import json
import RPi.GPIO as GPIO
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532
import logging
import actionHandler
PWM = True

def pid_poller_loop(sub_addr, queue):
    '''This is a modified version of the default subscription poller loop that adds in feedback
    functionality.

    Callbacks must return a processed measurement result which is fed into a PID controller.
    The measurement object needs to be formatted as:
    {
        time: (measurement time stamp (s))
        measurement: (data),
        name: (unique name for pid controller),
        channel: (pid channel),
        config: (channel configParser obj)
    }
    '''
    log = logging.getLogger('poller')
    log.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    log.addHandler(ch)
    # a hash table (dict) of callbacks to perform when a message is recieved
    # the hash is the data stream filter, the value is a list of callbacks
    subscriptions = {}
    pids = {}
    GPIO.setmode(GPIO.BOARD)  # define the pin numbering (i think)
    # TODO: read off of config [MAIN]
    if not PWM:
        error_pin = 10  # GPIO pin number for error signal output
        GPIO.setup(error_pin, GPIO.OUT)
        GPIO.output(error_pin, False)
    else:
        error_pin = 12  # GPIO pin number for error signal output
        GPIO.setup(error_pin, GPIO.OUT)
        pwm_ch = GPIO.PWM(error_pin, 1000)  # GPIO pin number for hardware PWM
        pwm_ch.start(0.)
    context = zmq.Context()
    sub_sock = context.socket(zmq.SUB)
    # listen for one second, before doing housekeeping
    sub_sock.setsockopt(zmq.RCVTIMEO, 1000)
    sub_sock.connect(sub_addr)
    global_err_state = False
    last_msg = time.time()
    sub_list = {}
    time.sleep(2)
    stream_filter = ''
    while True:
        # process new command messages from the parent process
        try:
            #get command from command queue
            cmd = queue.get_nowait()
            if cmd['action'] == 'SHUTDOWN':
                break
            stream_filter = actionHandler.genericHandler(sub_sock, cmd, log, subscriptions, sub_list, stream_filter)

        except multiprocessing.queues.Empty:
            pass
        except IOError:
            log.error('IOError, probably a broken pipe. Exiting..')
            #sys.exit(1)
        except:
            log.exception("error encountered")

        # process data from the stream
        actionHandler.PID_Handler(sub_sock, global_err_state, last_msg, log, pids, subscriptions, PWM, pwm_ch, stream_filter)

    log.info('Shutting down poller loop.')
    sub_sock.close()
    context.term()
    GPIO.cleanup()
