from datetime import datetime, timezone
import paho.mqtt
import paho.mqtt.client as mqtt
import json
import random
import config
from sinks import sinkadapters

if __name__ == '__main__':
    for p in sinkadapters.sinks:
        inst = p()
        inst.start()

class subscription():
    def __init__(self):
        self.topic = None
        self.member = None
        self.sink = None
        self.label = None
        self.command = None

mqtt_broker = config.mqtt["broker"]
mqtt_client = config.mqtt["clientid"] + f'{random.randint(0, 1000)}'
mqtt_subscriptions = config.subscriptions

def make_datetime_utc():
    return datetime.now(timezone.utc).replace(tzinfo=timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') 

def search_json(data, member):
    for key, value in data.items():
        if key == member:
            return value

def on_message(client, userdata, message):
    msg = str(message.payload.decode("utf-8"))
    print(f"=== Received MQTT message at {make_datetime_utc()}")
    print(msg)
    # Check if there's sink configuration
    for sub in mqtt_subscriptions:
        if sub["topic"] == message.topic:
            msg_sub = sub
            # Make sure there's a label, default to topic name
            if msg_sub["label"] == None:
                msg_sub["label"] = msg_sub["topic"]
    # Figure out what kind of value to extract
    if msg_sub["member"] == None or msg_sub["member"] == "":
        print ("No message member defined, using raw value")
        value = msg
    else:
        # Check if the payload contains the configured member and parse out its avlue
        print ("Searching for JSON payload member: " + msg_sub["member"])
        data = json.loads(msg)
        #TODO: error handling
        member_parts = msg_sub["member"].split(".")
        for member in member_parts:
            data = search_json(data, member)
        value = data
        print ("Discovered value:", value)

    # Check if we have a place to send the data
    if isinstance(msg_sub["sink"], list):
        print ("Using multiple sinks:", json.dumps(msg_sub["sink"]))
    else:
        print ("Using sink: ", msg_sub["sink"])
    
    # Check if that requested sink adapter exists and write to it
    for config_sink in msg_sub["sink"]:
        for sink in sinkadapters.sinks:
            if sink.name.lower() == config_sink.lower():
                print (f"Sending {value} to {sink.name}")
                sink.write(sink, make_datetime_utc(), value, msg_sub)
    print("=== Done processing message")

print(f"Connecting paho-mqtt version: {paho.mqtt.__version__} with client id {mqtt_client}")
if paho.mqtt.__version__[0] > '1':
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, mqtt_client)
else:
    client = mqtt.Client(mqtt_client)

client.connect(mqtt_broker)
for sub in mqtt_subscriptions:
    print("Subscribing to: ", sub["topic"])
    client.subscribe(str(sub["topic"]))
client.on_message=on_message
client.loop_forever()
