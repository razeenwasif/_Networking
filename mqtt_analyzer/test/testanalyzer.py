# testanalyzer.py
import paho.mqtt.client as mqtt
import time
import sys

BROKER_ADDRESS = "localhost"
BROKER_PORT = 1883
CLIENT_ID = "wireshark_ana_client"
RECEIVED_MESSAGE = False

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"analyzer ({CLIENT_ID}): Connected to MQTT Broker!")
        topic_to_subscribe = userdata["topic"]
        qos_to_subscribe = userdata["qos"]
        print(f"analyzer ({CLIENT_ID}): Subscribing to '{topic_to_subscribe}' with QoS {qos_to_subscribe}")
        client.subscribe(topic_to_subscribe, qos=qos_to_subscribe)
    else:
        print(f"analyzer ({CLIENT_ID}): Failed to connect, return code {rc}")

def on_subscribe(client, userdata, mid, reason_code_list, properties=None):
    if reason_code_list[0].is_failure:
        print(f"analyzer ({CLIENT_ID}): Subscription failed: {reason_code_list[0]}")
    else:
        print(f"analyzer ({CLIENT_ID}): Successfully subscribed with MID {mid}")

def on_message(client, userdata, msg):
    global RECEIVED_MESSAGE
    print(f"analyzer ({CLIENT_ID}): Received message! Topic: {msg.topic}, QoS: {msg.qos}, Payload: {msg.payload.decode()}")
    RECEIVED_MESSAGE = True

def subscribe_and_receive(topic_to_subscribe, qos_level):
    global RECEIVED_MESSAGE
    RECEIVED_MESSAGE = False

    user_data = {"topic": topic_to_subscribe, "qos": qos_level}
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID, userdata=user_data)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_subscribe = on_subscribe

    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    except Exception as e:
        print(f"analyzer ({CLIENT_ID}): Error connecting to broker: {e}")
        return

    client.loop_start()

    timeout_seconds = 10
    start_wait_time = time.time()
    while not RECEIVED_MESSAGE and (time.time() - start_wait_time) < timeout_seconds:
        time.sleep(0.1)

    if not RECEIVED_MESSAGE:
        print(f"analyzer ({CLIENT_ID}): Did not receive a message on '{topic_to_subscribe}' within {timeout_seconds}s.")

    time.sleep(1) 
    client.loop_stop()
    client.disconnect()
    print(f"analyzer ({CLIENT_ID}): Disconnected.")


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python wireshark_test_analyzer.py <topic_to_subscribe> <qos_to_subscribe>")
        print("Example (QoS 0): python wireshark_test_analyzer.py test/qos0 0")
        print("Example (QoS 1): python wireshark_test_analyzer.py test/qos1 1")
        print("Example (QoS 2): python wireshark_test_analyzer.py test/qos2 2")
        sys.exit(1)

    topic_sub = sys.argv[1]
    qos_sub = int(sys.argv[2])

    if qos_sub not in [0, 1, 2]:
        print("Error: Subscription QoS level must be 0, 1, or 2.")
        sys.exit(1)

    subscribe_and_receive(topic_sub, qos_sub)
