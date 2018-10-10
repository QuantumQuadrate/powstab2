import zmq
import time
import json
import RPi.GPIO as GPIO
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532
import requests
stream_filter = ''


class generic_Handler(object):
    """docstring for genericHandler."""

    def __init__(self, log):
        self.log = log
        self.subscriptions = {}
        self.sub_list = {}
        self.stream_filter = ''

    def handle(self, cmd, sub_sock):
        print sub_sock
        self.sub_sock = sub_sock
        if cmd['action'] == 'SUBSCRIBE':
            msg = 'Subscribing with stream filter: [{}]'
            stream_filter = cmd['stream_filter']
            self.log.info(msg.format(stream_filter))

            # add the callback to the list of things to do for the stream
            if stream_filter not in self.subscriptions:
                self.subscriptions[stream_filter] = []
                # stream_filter is assigned as a key with an empty list
                self.sub_sock.setsockopt_string(zmq.SUBSCRIBE, stream_filter)
            self.subscriptions[stream_filter].append({
                'callback': cmd['callback'],
                'kwargs': cmd['kwargs'],
                'state': {},
                'control': {'alert': True, 'pause': False},
                'id': cmd['id']
            })

            # add subscribed channel info to dict
            # sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}
            self.sub_list[cmd['id']] = {
                'kwargs': cmd['kwargs'],
                'control': {'alert': True, 'pause': False}}
            self.log.info("subscriptions: {}".format(self.subscriptions[stream_filter]))

        if cmd['action'] == 'UPDATE_KW':
            msg = 'Updating channel...'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[stream_filter]:
                if cb['id'] == cmd['id']:
                    cb['kwargs'] = cmd['kwargs']
                    # self.sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}
                    self.sub_list[cmd['id']] = {
                        'control': cb['control'],
                        'kwargs': cmd['kwargs']
                    }
            self.log.info("subscriptions: {}".format(self.subscriptions[stream_filter]))

        if (cmd['action'] == 'UNSUBSCRIBE' or
                cmd['action'] == 'REMOVE_ALL_CBS'):
            msg = 'Unsubscribing to stream filter: [{}]'
            self.log.info(msg.format(cmd['stream_filter']))
            self.sub_sock.setsockopt_string(zmq.UNSUBSCRIBE, stream_filter)

        if cmd['action'] == 'REMOVE_ALL_CBS':
            msg = 'Removing all callbacks for stream filter: [{}]'
            self.log.info(msg.format(cmd['stream_filter']))
            del self.subscriptions[cmd['stream_filter']]

        if cmd['action'] == 'RESET':
            msg = 'Resetting channel'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[stream_filter]:
                # cb is a dict with all the info of each channel subscribed
                # stream_filter is a list of all the cb dict.
                if cb['id'] == cmd['id']:
                    cb['state'] = {}
            self.log.info("subscriptions: {}".format(self.subscriptions[stream_filter]))

        if cmd['action'] == 'RESET_ALL':
            msg = 'Resetting all channels'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[stream_filter]:
                # cb is a dict with all the info of each channel subscribed
                # stream_filter is a list of all the cb dict.
                cb['state'] = {}
            self.log.info("subscriptions: {}".format(self.subscriptions[stream_filter]))

        if (cmd['action'] == 'MUTE' or
                cmd['action'] == 'UNMUTE'):
            msg = 'Muted channel alert'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[stream_filter]:
                if cb['id'] == cmd['id']:
                    cb['control']['alert'] = (cmd['action'] == 'UNMUTE')
                    self.sub_list[cmd['id']] = {
                        'control': cb['control'],
                        'kwargs': cb['kwargs']
                    }

        if (cmd['action'] == 'MUTE_ALL' or
                cmd['action'] == 'UNMUTE_ALL'):
            msg = 'Muted/Unmuted all channel alert'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[stream_filter]:
                cb['control']['alert'] = (cmd['action'] == 'UNMUTE_ALL')
                self.sub_list[cb['id']] = {
                    'control': cb['control'],
                    'kwargs': cb['kwargs']
                }

        if (cmd['action'] == 'PAUSE_ALL' or
                cmd['action'] == 'RESTART_ALL'):
            msg = 'Paused/ Restarted all channels'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[stream_filter]:
                cb['control']['pause'] = (cmd['action'] == 'PAUSE_ALL')
                self.sub_list[cb['id']] = {
                    'control': cb['control'],
                    'kwargs': cb['kwargs']
                }

        if (cmd['action'] == 'PAUSE' or
                cmd['action'] == 'RESTART'):
            msg = 'Paused/Restarted this channel'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[stream_filter]:
                if cb['id'] == cmd['id']:
                    cb['control']['pause'] = (cmd['action'] == 'PAUSE')
                    self.sub_list[cmd['id']] = {
                        'control': cb['control'],
                        'kwargs': cb['kwargs']
                    }
        sub_list_json = json.dumps(self.sub_list)
        requests.put('http://127.0.0.1:5000/monitor', json=sub_list_json)
        return stream_filter


class PID_Handler(object):
    """docstring for ."""
    def __init__(self, log):
        # a hash table (dict) of callbacks to perform when a message is recieved
        # the hash is the data stream filter, the value is a list of callbacks
        self.PWM = True
        self.pids = {}
        self.global_err_state = False
        self.last_msg = time.time()
        time.sleep(2)
        self.stream_filter = ''
        self.log = log
        self.pwm_ch = False
        GPIO.setmode(GPIO.BOARD)  # define the pin numbering (i think)
        # TODO: read off of config [MAIN]
        if not self.PWM:
            self.error_pin = 10  # GPIO pin number for error signal output
            GPIO.setup(self.error_pin, GPIO.OUT)
            GPIO.output(self.error_pin, False)
        else:
            self.error_pin = 12  # GPIO pin number for error signal output
            GPIO.setup(self.error_pin, GPIO.OUT)
            self.pwm_ch = GPIO.PWM(self.error_pin, 1000)  # GPIO pin number for hardware PWM
            self.pwm_ch.start(0.)

    def handle(self, subscriptions, sub_sock, conMan):
        try:
            [streamID, content] = sub_sock.recv_multipart()

            self.last_msg = time.time()
            try:
                self.log.debug("new data")
                for cb in subscriptions[streamID]:
                    result = cb['callback'](streamID, json.loads(content), self.log, **cb['kwargs'])
                    pid_ctrl_name = result['name']

                    # check if pid controller exists
                    if pid_ctrl_name not in self.pids:
                        # if it doesn't make a new controller
                        self.pids[pid_ctrl_name] = {'err_state': False}
                        fb_type = conMan.config.get(result['name'], 'FeedbackDevice')
                        self.log.debug('recieved first instance from channel: {} type: {}'.format(pid_ctrl_name, fb_type))
                        print "\n \n \n"
                        print result
                        print "\n \n \n"
                        if fb_type == WK10CR1.type:
                            self.pids[pid_ctrl_name]['pid'] = WK10CR1(result['channel'], conMan.config, logger=self.log)
                        if fb_type == WDAC8532.type:
                            self.pids[pid_ctrl_name]['pid'] = WDAC8532(result['channel'], conMan.config, logger=self.log)
                    # update with new info, save error state
                    try:
                        print self.pids
                        self.pids[pid_ctrl_name]['pid'].updateConfig()
                        self.pids[pid_ctrl_name]['err_state'] = self.pids[pid_ctrl_name]['pid'].update(result)
                    except:
                        self.log.exception('Unhandled server exception in pid: `{}`'.format(pid_ctrl_name))

            except KeyError:
                msg = "An unrecognized streamID `{}` was encountered"
                self.log.error(msg.format(streamID))
                self.log.error(subscriptions)

            # or all pid error states and set error pin accordingly
            self.last_g_err_state = self.global_err_state
            self.global_err_state = False
            for ch in self.pids:
                self.global_err_state = self.global_err_state or self.pids[ch]['err_state']
                if self.pids[ch]['err_state']:
                    self.log.info('{} is bad and should feel bad: err {:05.3f}'.format(ch, self.pids[ch]['pid'].pid.last_error))

            if self.global_err_state != self.last_g_err_state:
                if not self.PWM:
                    GPIO.output(self.error_pin, self.global_err_state)
                else:
                    if self.global_err_state:
                        self.log.info('trying to turn on the pwm output')
                        self.pwm_ch.ChangeDutyCycle(50.)  # 50% duty cycle pwm output
                    else:
                        self.pwm_ch.ChangeDutyCycle(0.)  # 0% duty cycle pwm output for no error

        except zmq.ZMQError as e:
            if e.errno != zmq.EAGAIN:
                self.log.exception("zmq error encountered")
            elif time.time() - self.last_msg > 20:
                self.pwm_ch.ChangeDutyCycle(50.)  # 50% duty cycle pwm output

        except:
            self.log.exception("error encountered")
