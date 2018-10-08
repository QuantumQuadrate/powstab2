import zmq
import multiprocessing
import sys
import time
import json
import RPi.GPIO as GPIO
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532
import logging

def genericHandler(sub_sock, queue, log):

    try:
        #get command from command queue
        cmd = queue.get_nowait()
        if cmd['action'] == 'SHUTDOWN':
            break

        if cmd['action'] == 'SUBSCRIBE':
            msg = 'Subscribing with stream filter: [{}]'
            stream_filter = cmd['stream_filter']
            log.info(msg.format(stream_filter))

            # add the callback to the list of things to do for the stream
            if stream_filter not in subscriptions:
                subscriptions[stream_filter] = []
                #stream_filter is assigned as a key with an empty list
                sub_sock.setsockopt_string(zmq.SUBSCRIBE, stream_filter)
            subscriptions[stream_filter].append({
                'callback': cmd['callback'],
                'kwargs': cmd['kwargs'],
                'state': {},
                'control': {'alert': True, 'pause': False},
                'id': cmd['id']
            })

            # add subscribed channel info to dict
            #sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}
            sub_list[cmd['id']] = {
                'kwargs': cmd['kwargs'],
                'control': {'alert': True, 'pause': False}
            }
            log.info("subscriptions: {}".format(subscriptions[stream_filter]))

        if cmd['action'] == 'UPDATE_KW':
            msg = 'Updating channel...'
            log.info(msg.format(cmd['stream_filter']))
            for cb in subscriptions[stream_filter]:
                if cb['id'] == cmd['id']:
                    cb['kwargs'] = cmd['kwargs']
                    #sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}
                    sub_list[cmd['id']]={
                        'control': cb['control'],
                        'kwargs': cmd['kwargs']
                    }
            log.info("subscriptions: {}".format(subscriptions[stream_filter]))


        if (cmd['action'] == 'UNSUBSCRIBE' or
                cmd['action'] == 'REMOVE_ALL_CBS'):
            msg = 'Unsubscribing to stream filter: [{}]'
            log.info(msg.format(cmd['stream_filter']))
            sub_sock.setsockopt_string(zmq.UNSUBSCRIBE, stream_filter)

        if cmd['action'] == 'REMOVE_ALL_CBS':
            msg = 'Removing all callbacks for stream filter: [{}]'
            log.info(msg.format(cmd['stream_filter']))
            del subscriptions[cmd['stream_filter']]

        if cmd['action'] == 'RESET':
            msg = 'Resetting channel'
            log.info(msg.format(cmd['stream_filter']))
            for cb in subscriptions[stream_filter]:
                #cb is a dict with all the info of each channel subscribed
                #stream_filter is a list of all the cb dict.
                if cb['id'] == cmd['id']:
                    cb['state']={}
            log.info("subscriptions: {}".format(subscriptions[stream_filter]))

        if cmd['action'] == 'RESET_ALL':
            msg = 'Resetting all channels'
            log.info(msg.format(cmd['stream_filter']))
            for cb in subscriptions[stream_filter]:
                #cb is a dict with all the info of each channel subscribed
                #stream_filter is a list of all the cb dict.
                cb['state']={}
            log.info("subscriptions: {}".format(subscriptions[stream_filter]))

        if (cmd['action'] == 'MUTE' or
                cmd['action'] == 'UNMUTE'):
            msg = 'Muted channel alert'
            log.info(msg.format(cmd['stream_filter']))
            for cb in subscriptions[stream_filter]:
                if cb['id'] == cmd['id']:
                    cb['control']['alert'] = (cmd['action'] == 'UNMUTE')
                    sub_list[cmd['id']]={
                        'control': cb['control'],
                        'kwargs': cb['kwargs']
                    }

        if (cmd['action'] == 'MUTE_ALL' or
                cmd['action'] == 'UNMUTE_ALL'):
            msg = 'Muted/Unmuted all channel alert'
            log.info(msg.format(cmd['stream_filter']))
            for cb in subscriptions[stream_filter]:
                cb['control']['alert'] = (cmd['action'] == 'UNMUTE_ALL')
                sub_list[cb['id']]={
                    'control': cb['control'],
                    'kwargs': cb['kwargs']
                }

        if (cmd['action'] == 'PAUSE_ALL' or
                cmd['action'] == 'RESTART_ALL'):
            msg = 'Paused/ Restarted all channels'
            log.info(msg.format(cmd['stream_filter']))
            for cb in subscriptions[stream_filter]:
                cb['control']['pause'] = (cmd['action'] == 'PAUSE_ALL')
                sub_list[cb['id']]={
                    'control': cb['control'],
                    'kwargs': cb['kwargs']
                }

        if (cmd['action'] == 'PAUSE' or
                cmd['action'] == 'RESTART'):
            msg = 'Paused/Restarted this channel'
            log.info(msg.format(cmd['stream_filter']))
            for cb in subscriptions[stream_filter]:
                if cb['id'] == cmd['id']:
                    cb['control']['pause'] = (cmd['action'] == 'PAUSE')
                    sub_list[cmd['id']]={
                        'control': cb['control'],
                        'kwargs': cb['kwargs']
                    }

        sub_list_json = json.dumps(sub_list)
        requests.put('http://127.0.0.1:5000/monitor', json=sub_list_json)

    except multiprocessing.queues.Empty:
        pass
    except IOError:
        log.error('IOError, probably a broken pipe. Exiting..')
        sys.exit(1)
    except:
        log.exception("error encountered")

    try:
        [streamID, content] = sub_sock.recv_multipart()
        try:
            log.debug("new data")
            for cb in subscriptions[streamID]:
                if cb['control']['pause'] == False:
                    cb['state'] = cb['callback'](
                        streamID, json.loads(content),
                        cb['state'], log, cb['control'], **cb['kwargs']
                    )
                else:
                    pass

        except KeyError:
            msg = "An unrecognized streamID `{}` was encountered"
            log.error(msg.format(streamID))
            log.error(subscriptions)
    except zmq.ZMQError as e:
        if e.errno != zmq.EAGAIN:
            log.exception("zmq error encountered")
    except:
        log.exception("error encountered")
