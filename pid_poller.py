import zmq
import multiprocessing
import sys
import json
from worker_K10CR1 import WK10CR1
from worker_DAC8532 import WDAC8532


def pid_poller_loop(sub_addr, queue, log):
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
    # a hash table (dict) of callbacks to perform when a message is recieved
    # the hash is the data stream filter, the value is a list of callbacks
    subscriptions = {}
    pids = {}
    context = zmq.Context()
    sub_sock = context.socket(zmq.SUB)
    # listen for one second, before doing housekeeping
    sub_sock.setsockopt(zmq.RCVTIMEO, 1000)
    sub_sock.connect(sub_addr)
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
            try:
                log.info("new data")
                for cb in subscriptions[streamID]:
                    result = cb['callback'](streamID, json.loads(content), log, **cb['kwargs'])
                    pid_ctrl_name = result['name']
                    # check if pid controller exists
                    if pid_ctrl_name not in pids:
                        # if it doesn't make a new controller
                        fb_type = result['config'].get(result['name'], 'FeedbackDevice')
                        if fb_type == WK10CR1.type:
                            pids[pid_ctrl_name] = WK10CR1(result['channel'], result['config'], logger=log)
                        if fb_type == WDAC8532.type:
                            pids[pid_ctrl_name] = WDAC8532(result['channel'], result['config'], logger=log)
                    # update with new info
                    try:
                        pids[pid_ctrl_name].update(result)
                    except:
                        log.exception('Unhandled server exception in pid: `{}`'.format(pid_ctrl_name))

            except KeyError:
                msg = "An unrecognized streamID `{}` was encountered"
                log.error(msg.format(streamID))
                log.error(subscriptions)
        except zmq.ZMQError as e:
            if e.errno != zmq.EAGAIN:
                log.exception("zmq error encountered")
        except:
            log.exception("error encountered")

    log.info('Shutting down poller loop.')
    sub_sock.close()
    context.term()
