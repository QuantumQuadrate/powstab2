#!/usr/bin/env python
from flask import Flask
from flask import render_template
from flask import request
import json
import numpy as np
import logging
import ConfigParser
from origin.client.origin_subscriber import Subscriber
from origin.client import server
from origin import current_time, TIMESTAMP
import pprint
import sys


def sendOutput(stream_id, data, state, log, inputs, matrix, config_file, outputs):
    # convert temp from mC to C
    print "made it this far"

    origin_config = ConfigParser.ConfigParser()
    origin_config.read(config_file)
    print data
    input_vector = []
    for input in inputs:
        input_vector.append(data[input])

    output_vector = np.matmul(np.asarray(matrix), np.asarray(input_vector))
    iter = 0
    ts = current_time(origin_config)
    data = {TIMESTAMP: ts}
    for output in output_vector:
        data.update({outputs[iter]: output})
        iter += 1

    self.connection.send(**data)
    print "\n"
    print data
    print "\n"
    print data

    return state


class Server(object):

    def runServer(self, sub, stream, conMan):

        app = Flask(__name__)

        # commands & webpage
        # home page "monitor"
        sub_file = 'subscriptions.json'
        with open(sub_file, 'w') as f:
            f.write('{}')
            f.close()

        # commands & webpage
        # home page "monitor"
        @app.route('/monitor', methods=['GET', 'PUT'])
        def monitor():
            # GET request string(json) needs to be save as file, to be read by flask template
            if request.method == "PUT":
                sub_list_json = request.get_json()
                with open(sub_file, 'w') as f:
                    f.write(sub_list_json)
                    f.close()
            with open(sub_file, 'r') as f:
                sub_list = json.load(f)

            # sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}
            return render_template('index.html', id_list= sub_list.keys(), sub_list= sub_list, **sub_list)
            # except Exception:
            #     return 'Unable to load page'

        # subscribe
        @app.route('/update/<id>', methods=['GET', 'POST'])
        def update(id):
            id = id.encode('ascii', 'ignore')
            with open(sub_file, 'r') as f:
                sub_list = json.load(f)
                # sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}

            if request.method == 'POST':
                sub_list[id]['kwargs'] = request.form.to_dict()
                sub.update(stream, int(id), **sub_list[id]['kwargs'])

            id_dict = sub_list[id]
            control = id_dict['control']
            kwargs = id_dict['kwargs']

            if control['alert']:
                alert = 'On'
            else:
                alert = 'Off'
            if control['pause']:
                pause = 'Paused'
            else:
                pause = 'Started'

            configStuff = conMan.config.items('CHANNEL'+str(kwargs['channel']))

            return render_template('keywords.html', id=id, kw_dict=kwargs, alert=alert, pause=pause, config_dict=configStuff)

        # subscribe
        @app.route('/update/<id>/config', methods=['POST'])
        def updateConfig(id):
            with open(sub_file, 'r') as f:
                sub_list = json.load(f)
            id_dict = sub_list[id]
            kwargs = id_dict['kwargs']
            configDict = request.form.to_dict()
            for key in configDict.keys():
                conMan.config.set('CHANNEL'+str(kwargs['channel']), key, configDict[key])
            conMan.updateConfig()
            return ''

        @app.route('/update/<id>/<action>/action', methods=['POST'])
        def unsubscribe(id, action):
            if action == "unsubscribe":
                sub.unsubscribe(stream, int(id))
            elif action == "resetall":
                sub.reset_all(stream)
            elif action == "mute":
                sub.mute(stream, int(id))
            elif action == "unmute":
                sub.unmute(stream, int(id))
            elif action == "muteall":
                sub.mute_all(stream)
            elif action == "unmuteall":
                sub.unmute_all(stream)
            elif action == "pause":
                sub.pause(stream, int(id))
            elif action == "pauseall":
                sub.pause_all(stream)
            elif action == "restart":
                sub.restart(stream, int(id))
            elif action == "restartall":
                sub.restart_all(stream)
            elif action == "reset":
                sub.reset(stream, int(id))
            else:
                return 'error'
            return ''

        app.run(host='0.0.0.0', debug=True, use_reloader=False)


class PIDServer(Server):

    def runServer(self, sub, stream, conMan):

        app = Flask(__name__)
        @app.route('/update/<id>/config', methods=['POST'])
        def updateConfig(id):
            with open(sub_file, 'r') as f:
                sub_list = json.load(f)
            id_dict = sub_list[id]
            print id_dict
            kwargs = id_dict['kwargs']
            configDict = request.form.to_dict()
            for key in configDict.keys():
                conMan.config.set('CHANNEL'+str(kwargs['channel']), key, configDict[key])
            conMan.updateConfig()
            return ''

        super(PIDServer, self).runServer(sub, stream, conMan)


class MatrixTransformServer(Server):

    def runServer(self, sub, stream, conMan):
        super(PIDServer, self).runServer(sub, stream, conMan)

    def setOriginConfig(self, config_file):
        self.origin_config = ConfigParser.ConfigParser()
        self.origin_config.read(config_file)

    def startClient(self, outputs, outputStream):

        serv = server(self.origin_config)
        records = {}
        for output in outputs:
            records.update({output: 'float'})

        self.connection = serv.registerStream(
            stream=outputStream,
            records=records)

    def startSub(self, dataStream):

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        sub = Subscriber(self.origin_config, self.logger)

        self.logger.info("streams")
        print('')
        pprint.pprint(sub.known_streams.keys())

        if dataStream not in sub.known_streams:
            print("stream not recognized")
            sub.close()
            sys.exit(1)

        print("subscribing to stream: %s" % (dataStream,))
        # can use arbitrary callback
        # if you need to use the same base callback for multiple streams pass in specific
        # parameters through kwargs
        sub.subscribe(dataStream, callback=sendOutput, inputs=self.inputs, matrix=self.matrix, config_file='origin-client.cfg', outputs=self.outputs)

    def setup(self, matrix, dataStream, inputs, outputs, outputStream):
        self.inputs = inputs
        self.outputs = outputs
        self.matrix = matrix
        self.dataStream = dataStream
        self.outputStream = outputStream
        self.setOriginConfig('origin-client.cfg')
        self.startClient(outputs, outputStream)
        self.startSub(dataStream)
