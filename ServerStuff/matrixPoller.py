import zmq
import multiprocessing
import RPi.GPIO as GPIO
import actionHandler
import logging
import json
import time
from origin.client.origin_server import server
PWM = True
outputStream = ''
outputs = ''
inputs = ''
matrix = ''
origin_config = ''


def matrix_poller_loop(sub_addr, queue):
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
    genHandler = actionHandler.generic_Handler(log)
    subscriptions = {}

    serv = server(origin_config)
    records = {}
    for output in outputs:
        records.update({output: 'float'})
    records = records
    clientConn = serv.registerStream(
        stream=outputStream,
        records=records)

    while True:
        # process new command messages from the parent process
        try:
            # get command from command queue
            cmd = queue.get_nowait()
            if cmd['action'] == 'SHUTDOWN':
                break
            genHandler.handle(cmd, sub_sock)
            subscriptions = genHandler.subscriptions
        except multiprocessing.queues.Empty:
            pass

        except IOError:
            log.error('IOError, probably a broken pipe. Exiting..')
            # sys.exit(1)
        except:
            log.exception("error encountered")

        # process data from the stream
        try:
            [streamID, content] = sub_sock.recv_multipart()

            try:
                log.debug("new data")
                for cb in subscriptions[streamID]:
                    data = cb['callback'](streamID, json.loads(content), origin_config, **cb["kwargs"])
                    clientConn.send(**data)
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
