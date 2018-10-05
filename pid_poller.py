import zmq
import multiprocessing
import sys
import time
import json
import RPi.GPIO as GPIO
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532
import logging
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
    while True:
        # process new command messages from the parent process
        try:
            cmd = queue.get_nowait()
            log.info(cmd)
            if cmd['action'] == 'SHUTDOWN':
                break

            if cmd['action'] == 'SUBSCRIBE':
                msg = 'Subscribing with stream filter: [{}]'
                stream_filter = cmd['stream_filter']
                print stream_filter
                log.info(msg.format(stream_filter))
                # add the callback to the list of things to do for the stream
                if stream_filter not in subscriptions:
                    subscriptions[stream_filter] = []
                    sub_sock.setsockopt_string(zmq.SUBSCRIBE, stream_filter)
                subscriptions[stream_filter].append({
                    'callback': cmd['callback'],
                    'kwargs': cmd['kwargs']
                })

                log.info("subscriptions: {}".format(subscriptions))

            if (cmd['action'] == 'UNSUBSCRIBE' or
                    cmd['action'] == 'REMOVE_ALL_CBS'):
                msg = 'Unsubscribing to stream filter: [{}]'
                log.info(msg.format(cmd['stream_filter']))
                sub_sock.setsockopt_string(zmq.UNSUBSCRIBE, stream_filter)

            if cmd['action'] == 'REMOVE_ALL_CBS':
                msg = 'Removing all callbacks for stream filter: [{}]'
                log.info(msg.format(cmd['stream_filter']))
                del subscriptions[cmd['stream_filter']]

        except multiprocessing.queues.Empty:
            pass
        except IOError:
            log.error('IOError, probably a broken pipe. Exiting..')
            sys.exit(1)
        except:
            log.exception("error encountered")

        # process data from the stream
        try:
            [streamID, content] = sub_sock.recv_multipart()

            last_msg = time.time()
            try:
                log.debug("new data")
                for cb in subscriptions[streamID]:
                    result = cb['callback'](streamID, json.loads(content), log, **cb['kwargs'])
                    pid_ctrl_name = result['name']
                    # check if pid controller exists
                    if pid_ctrl_name not in pids:
                        # if it doesn't make a new controller
                        pids[pid_ctrl_name] = {'err_state': False}
                        fb_type = result['config'].get(result['name'], 'FeedbackDevice')
                        log.debug('recieved first instance from channel: {} type: {}'.format(pid_ctrl_name, fb_type))
                        if fb_type == WK10CR1.type:
                            pids[pid_ctrl_name]['pid'] = WK10CR1(result['channel'], result['config'], logger=log)
                        if fb_type == WDAC8532.type:
                            pids[pid_ctrl_name]['pid'] = WDAC8532(result['channel'], result['config'], logger=log)
                    # update with new info, save error state
                    try:
                        pids[pid_ctrl_name]['err_state'] = pids[pid_ctrl_name]['pid'].update(result)
                    except:
                        log.exception('Unhandled server exception in pid: `{}`'.format(pid_ctrl_name))

            except KeyError:
                msg = "An unrecognized streamID `{}` was encountered"
                log.error(msg.format(streamID))
                log.error(subscriptions)

            # or all pid error states and set error pin accordingly
            last_g_err_state = global_err_state
            global_err_state = False
            for ch in pids:
                global_err_state = global_err_state or pids[ch]['err_state']
                if pids[ch]['err_state']:
                    log.info('{} is bad and should feel bad: err {:05.3f}'.format(ch, pids[ch]['pid'].pid.last_error))

            if global_err_state != last_g_err_state:
                if not PWM:
                    GPIO.output(error_pin, global_err_state)
                else:
                    if global_err_state:
                        log.info('trying to turn on the pwm output')
                        pwm_ch.ChangeDutyCycle(50.)  # 50% duty cycle pwm output
                    else:
                        pwm_ch.ChangeDutyCycle(0.)  # 0% duty cycle pwm output for no error

        except zmq.ZMQError as e:
            if e.errno != zmq.EAGAIN:
                log.exception("zmq error encountered")
            elif time.time() - last_msg > 20:
                pwm_ch.ChangeDutyCycle(50.)  # 50% duty cycle pwm output

        except:
            log.exception("error encountered")

    log.info('Shutting down poller loop.')
    sub_sock.close()
    context.term()
    GPIO.cleanup()
