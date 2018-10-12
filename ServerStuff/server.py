#!/usr/bin/env python
from flask import Flask
from flask import render_template
from flask import request
import json


def runServer(sub, stream, conMan):

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
        return render_template('index.html', id_list = sub_list.keys(), **sub_list)
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
        print id_dict
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

    app.run(host='0.0.0.0', debug=True)
