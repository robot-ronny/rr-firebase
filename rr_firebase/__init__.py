#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import click
import click_log
import logging
import datetime
import json
import sys
import time
import paho.mqtt.client
import firebase_admin
import firebase_admin.db
import firebase_admin.credentials
import firebase_admin.storage


__version__ = '@@VERSION@@'


def mqtt_on_connect(mqttc, userdata, flags, rc):
    logging.info('Connected to MQTT broker with code %s', rc)

    topics = ("node/#", "ronny/camera/object-detected", 'ronny/camera/foto')

    for topic in topics:
        logging.debug('Subscribe: %s', topic)
        mqttc.subscribe(topic)


def mqtt_on_disconnect(mqttc, userdata, rc):
    logging.info('Disconnect from MQTT broker with code %s', rc)


@click.command()
@click.option('--firebase', 'firebase_url', help="Firebase url", required=True)
@click.option("--credentials", 'credentials_file', help="Firebase credentials file path", required=True, type=click.Path(exists=True))
@click.option('--host', 'mqtt_host', type=click.STRING, default="127.0.0.1", help="MQTT host to connect to [default: 127.0.0.1].")
@click.option('--port', 'mqtt_port', type=click.IntRange(0, 65535), default=1883, help="MQTT port to connect to [default: 1883].")
@click.option('--username', type=click.STRING, help="MQTT username.")
@click.option('--password', type=click.STRING, help="MQTT password.")
@click.option('--cafile', type=click.Path(exists=True), help="MQTT cafile.")
@click.option('--certfile', type=click.Path(exists=True), help="MQTT certfile.")
@click.option('--keyfile', type=click.Path(exists=True), help="MQTT keyfile.")
@click.version_option(version=__version__)
@click_log.simple_verbosity_option(default='INFO')
def cli(firebase_url, credentials_file, mqtt_host, mqtt_port, username, password, cafile, certfile, keyfile):
    '''Roony tool for firebase'''

    logging.info("Process started")

    cred = firebase_admin.credentials.Certificate(credentials_file)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://' + firebase_url + ".firebaseio.com",
        'storageBucket': firebase_url + '.appspot.com'
    })

    db = firebase_admin.db.reference("/")
    bucket = firebase_admin.storage.bucket()


    def on_message(mqttc, obj, msg):
        logging.debug('Message %s %s', msg.topic, msg.payload)

        payload = json.loads(msg.payload.decode("utf-8"))

        if msg.topic.startswith("node/"):
            split_topic = msg.topic.split("/")
            quantitie = split_topic[4]
            db.update({"sensors/ronny/" + quantitie: payload})

        elif msg.topic == "ronny/camera/object-detected":
            db.update({"camera": {"object_detected": payload}})

        elif msg.topic == "ronny/camera/foto":
            logging.debug('aaaa')
            blob = bucket.blob('image.PNG')
            with open('/run/user/1000/img.jpg', 'rb') as my_file:
                blob.upload_from_file(my_file)

    mqttc = paho.mqtt.client.Client()
    mqttc.on_connect = mqtt_on_connect
    mqttc.on_disconnect = mqtt_on_disconnect
    mqttc.on_message = on_message

    if username:
        mqttc.username_pw_set(username, password)

    if cafile:
        mqttc.tls_set(cafile, certfile, keyfile)

    mqttc.connect(mqtt_host, mqtt_port, keepalive=10)
    mqttc.loop_start()

    cache = {
        '/commands/go/value': 10,
        '/commands/go/direction': 'forward',
    }

    def getPayload(path, data):
        response = {}
        if isinstance(data, dict):
            for k in data:
                response.update(getPayload(path + '/' + k if path[-1] != '/' else path + k, data[k]))
        else:
            response[path] = data
        return response

    def callback(msg):
        logging.debug("fb: %s %s", msg.path, msg.data)

        payload = getPayload(msg.path, msg.data)

        cache.update(payload)

        logging.debug("cache: %s", cache)

        if msg.path.startswith("/commands/go"):
            payload = {'interval': cache['/commands/go/value'], 'speed': 100}
            mqttc.publish("ronny/go/" + cache['/commands/go/direction'], json.dumps(payload))

        elif msg.path == '/gesture/name':
            mqttc.publish("ronny/gesture", cache['/gesture/name'])

    db.listen(callback)


def main():
    try:
        cli()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        click.echo(str(e), err=True)
        if "DEBUG" in sys.argv:
            raise e
        sys.exit(1)
