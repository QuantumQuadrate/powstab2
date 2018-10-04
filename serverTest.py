#!/usr/bin/env python

import sys
import os.path
import ConfigParser
import pprint
import logging
import time
import numpy as np
import requests
import json
import ast
from flask import Flask
from flask import render_template
from flask import request
from origin.client.origin_subscriber import Subscriber

def test(stream_id, data, state, log, control, buflen=100, trigstd=3, init=30, ch=None ,filename=None,adrs=None):
    """
    buflen is the length of the circular buffer
    trigstd is units of std deviation from average
    init is the index of initial elements filled in buffer before sending alarm
    ch is the channel number,ch=str,data[ch]=float,
    filename is name of saved csv file
    """

    adrs = str(adrs)

    try:
        print data
    except KeyError:
        log.error('Problem accessing key. Are you subscribed to the right stream?')
    return state

if __name__ == '__main__':
#web server
    app = Flask(__name__)
    sub_file = 'subscriptions.json'
    with open(sub_file, 'w') as f:
        f.write('{}')

    #commands & webpage
    #home page "monitor"
    @app.route('/monitor', methods=['GET','PUT'])
    def monitor():
        #GET request string(json) needs to be save as file, to be read by flask template
        if request.method == "PUT":
            sub_list_json = request.get_json()
            with open(sub_file, 'w') as f:
                f.write(sub_list_json)
        with open(sub_file, 'r') as f:
            sub_list = json.load(f)
        #sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}
        num_ch = len(sub_list)
        return render_template('index.html', id_list = sub_list.keys(), **sub_list)
        # except Exception:
        #     return 'Unable to load page'

    #subscribe
    @app.route('/update/<id>', methods=['GET', 'POST'])
    def update(id):
        id=id.encode('ascii','ignore')
        with open(sub_file, 'r') as f:
            sub_list = json.load(f)
            #sub_list = {1:{'kwargs':{kwargs}, 'control':{control}}

        if request.method == 'POST':
            sub_list[id]['kwargs'] = request.form.to_dict()
            sub.update(stream, int(id), **sub_list[id]['kwargs'])

        id_dict = sub_list[id]
        control = id_dict['control']
        kwargs = id_dict['kwargs']

        if control['alert'] == True:
            alert = 'On'
        else:
            alert = 'Off'

        if control['pause'] == True:
            pause = 'Paused'
        else:
            pause = 'Started'

        return render_template('keywords.html', id=id, kw_dict=kwargs, alert=alert, pause=pause)

    # @app.route('/monitor/subscribe/<ch>')
    # def sub_ch(ch):
    #     sub.subscribe(stream, )

    #unsubscribe
    #mute alert
    @app.route('/update/<id>/mute')
    def mute(id):
        sub.mute(stream, int(id))
        return render_template('commands.html', id=id, action='muted this channel')

    @app.route('/update/<id>/unmute')
    def unmute(id):
        sub.unmute(stream, int(id))
        return render_template('commands.html', id=id, action='Unmuted this channel')

    #mute all channels alert
    @app.route('/update/<id>/muteall')
    def mute_all(id):
        sub.mute_all(stream)
        return render_template('commands.html', id=id, action='Muted all Channels')

    @app.route('/update/<id>/unmuteall')
    def unmute_all(id):
        sub.unmute_all(stream)
        return render_template('commands.html', id=id, action='Unmuted all Channels')

    #Pause channel: stop getting data from the channel
    @app.route('/update/<id>/pause')
    def pause(id):
        sub.pause(stream, int(id))
        return render_template('commands.html', id=id, action='Paused this channel')

    #pause all channels
    @app.route('/update/<id>/pauseall')
    def pause_all(id):
        sub.pause_all(stream)
        return render_template('commands.html', id=id, action='Paused all Channels')

    #restart channel: restart receiving data from the channel
    @app.route('/update/<id>/restart')
    def restart(id):
        sub.restart(stream, int(id))
        return render_template('commands.html', id=id, action='Restarted this channel')

    #restart all channels
    @app.route('/update/<id>/restartall')
    def restart_all(id):
        sub.restart_all(stream)
        return render_template('commands.html', id=id, action='Restarted all Channels')

    #reset:
    @app.route('/update/<id>/reset')
    def reset(id):
        sub.reset(stream, int(id))
        return render_template('commands.html', id=id, action='Reseted channel data')
    #reset all channels
    @app.route('/update/<id>/resetall')
    def reset_all(id):
        sub.reset_all(stream)
        return render_template('commands.html', id=id, action='Reseted all channels data')

    @app.route('/update/<id>/unsubscribe')
    def unsubscribe(id):
        sub.unsubscribe(stream)
        return render_template('commands.html', id=id, action='Unsubscribed all channels')


    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    fLog = logging.FileHandler("f.log")
    fLog.setLevel(logging.DEBUG)
    fLog.setFormatter(formatter)
    logger.addHandler(fLog)

    # first find ourself
    fullBinPath = os.path.abspath(os.getcwd() + "/" + sys.argv[0])
    fullBasePath = os.path.dirname(os.path.dirname(fullBinPath))
    fullCfgPath = os.path.join(fullBasePath, "config")

    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            configfile = os.path.join(fullCfgPath, "origin-server-test.cfg")
        else:
            configfile = os.path.join(fullCfgPath, sys.argv[1])
    else:
        configfile = os.path.join(fullCfgPath, "origin-server.cfg")

    config = ConfigParser.ConfigParser()
    config.read(configfile)

    sub = Subscriber(config, logger)

    logger.info("streams")
    print('')
    pprint.pprint(sub.known_streams.keys())

    stream = 'toy'

    if stream not in sub.known_streams:
        print("stream not recognized")
        sub.close()
        sys.exit(1)

    print("subscribing to stream: %s" % (stream,))
    # sub.subscribe(stream)
    # can use arbitrary callback
    # if you need to use the same base callback for multiple streams pass in specific
    # parameters through kwargs
    sub.subscribe(stream, callback=test, buflen=200, trigstd=12, init=30, adrs=None)




    app.run()
    sub.close()
    logger.info('closing')
