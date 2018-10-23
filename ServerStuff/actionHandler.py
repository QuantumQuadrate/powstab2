import zmq
import json
import requests
import time


class generic_Handler(object):
    """docstring for genericHandler."""

    def __init__(self, log):
        self.log = log
        self.subscriptions = {}
        self.sub_list = {}
        self.stream_filter = ''

    def handle(self, cmd, sub_sock):
        self.sub_sock = sub_sock
        if cmd['action'] == 'SUBSCRIBE':
            msg = 'Subscribing with stream filter: [{}]'
            self.stream_filter = cmd['stream_filter']
            self.log.info(msg.format(self.stream_filter))

            # add the callback to the list of things to do for the stream
            if self.stream_filter  not in self.subscriptions:
                self.subscriptions[self.stream_filter] = []
                # stream_filter is assigned as a key with an empty list
                self.sub_sock.setsockopt_string(zmq.SUBSCRIBE, self.stream_filter)
            self.subscriptions[self.stream_filter].append({
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
            self.log.info("subscriptions: {}".format(self.subscriptions[self.stream_filter]))

        if cmd['action'] == 'UPDATE_KW':
            msg = 'Updating channel...'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[self.stream_filter]:
                if cb['id'] == cmd['id']:
                    cb['kwargs'] = cmd['kwargs']
                    # self.sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}
                    self.sub_list[cmd['id']] = {
                        'control': cb['control'],
                        'kwargs': cmd['kwargs']
                    }
            self.log.info("subscriptions: {}".format(self.subscriptions[self.stream_filter]))

        if (cmd['action'] == 'UNSUBSCRIBE' or
                cmd['action'] == 'REMOVE_ALL_CBS'):
            msg = 'Unsubscribing to stream filter: [{}]'
            self.log.info(msg.format(cmd['stream_filter']))
            self.sub_sock.setsockopt_string(zmq.UNSUBSCRIBE, self.stream_filter)

        if cmd['action'] == 'REMOVE_ALL_CBS':
            msg = 'Removing all callbacks for stream filter: [{}]'
            self.log.info(msg.format(cmd['stream_filter']))
            del self.subscriptions[cmd['stream_filter']]

        if cmd['action'] == 'RESET':
            msg = 'Resetting channel'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[self.stream_filter]:
                # cb is a dict with all the info of each channel subscribed
                # stream_filter is a list of all the cb dict.
                if cb['id'] == cmd['id']:
                    cb['state'] = {}
            self.log.info("subscriptions: {}".format(self.subscriptions[self.stream_filter]))

        if cmd['action'] == 'RESET_ALL':
            msg = 'Resetting all channels'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[self.stream_filter]:
                # cb is a dict with all the info of each channel subscribed
                # stream_filter is a list of all the cb dict.
                cb['state'] = {}
            self.log.info("subscriptions: {}".format(self.subscriptions[self.stream_filter]))

        if (cmd['action'] == 'MUTE' or
                cmd['action'] == 'UNMUTE'):
            msg = 'Muted channel alert'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[self.stream_filter]:
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
            for cb in self.subscriptions[self.stream_filter]:
                cb['control']['alert'] = (cmd['action'] == 'UNMUTE_ALL')
                self.sub_list[cb['id']] = {
                    'control': cb['control'],
                    'kwargs': cb['kwargs']
                }

        if (cmd['action'] == 'PAUSE_ALL' or
                cmd['action'] == 'RESTART_ALL'):
            msg = 'Paused/ Restarted all channels'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[self.stream_filter]:
                cb['control']['pause'] = (cmd['action'] == 'PAUSE_ALL')
                self.sub_list[cb['id']] = {
                    'control': cb['control'],
                    'kwargs': cb['kwargs']
                }

        if (cmd['action'] == 'PAUSE' or
                cmd['action'] == 'RESTART'):
            msg = 'Paused/Restarted this channel'
            self.log.info(msg.format(cmd['stream_filter']))
            for cb in self.subscriptions[self.stream_filter]:
                if cb['id'] == cmd['id']:
                    cb['control']['pause'] = (cmd['action'] == 'PAUSE')
                    self.sub_list[cmd['id']] = {
                        'control': cb['control'],
                        'kwargs': cb['kwargs']
                    }
        sub_list_json = json.dumps(self.sub_list)
        post_addr = 'http://127.0.0.1:5000/monitor'
        try:
            requests.put(post_addr, json=sub_list_json)
        except IOError:
            self.log.error('Communication with monitor port failed, waiting and retrying.')
            time.sleep(0.1)
            requests.put(post_addr, json=sub_list_json)
        return self.stream_filter
