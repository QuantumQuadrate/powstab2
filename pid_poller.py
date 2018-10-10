import zmq
import multiprocessing
import RPi.GPIO as GPIO
import actionHandler
import logging
PWM = False

def pid_poller_loop(sub_addr, queue):
    '''This is a modified version of the default subscription poller
     loop that adds in feedback functionality.

    Callbacks must return a processed measurement result which is fed into a
    PID controller. The measurement object needs to be formatted as:
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

    context = zmq.Context()
    sub_sock = context.socket(zmq.SUB)
    sub_sock.setsockopt(zmq.RCVTIMEO, 1000)
    sub_sock.connect(sub_addr)

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

    genHandler = actionHandler.generic_Handler(sub_sock, log)
    pidHandler = actionHandler.PID_Handler(sub_sock, log, pwm_ch)
    while True:
        # process new command messages from the parent process
        try:
            # get command from command queue
            cmd = queue.get_nowait()
            if cmd['action'] == 'SHUTDOWN':
                break
            genHandler.handle(cmd)
        except multiprocessing.queues.Empty:
            pass

        except IOError:
            log.error('IOError, probably a broken pipe. Exiting..')
            # sys.exit(1)
        except:
            log.exception("error encountered")

        # process data from the stream
        pidHandler.handle(genHandler.subscriptions)

    log.info('Shutting down poller loop.')
    sub_sock.close()
    context.term()
    GPIO.cleanup()
