import paho.mqtt.client as mqtt
import time
import sys

BROKER_ADDRESS = "localhost"
BROKER_PORT = 1883
CLIENT_ID = "wireshark_pub_client"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"Publisher ({CLIENT_ID}): Connected to MQTT Broker!")
    else:
        print(f"Publisher ({CLIENT_ID}): Failed to connect, return code {rc}")

def on_publish(client, userdata, mid, rc, properties=None):
    if rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"Publisher ({CLIENT_ID}): Message {mid} published successfully.")
    else:
        print(f"There was an issue")

def publish_single_message(topic_to_publish, message_payload, qos_level):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLIENT_ID)
    client.on_connect = on_connect
    client.on_publish = on_publish

    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    except Exception as e:
        print(f"Publisher ({CLIENT_ID}): Error connecting to broker: {e}")
        return

    client.loop_start() 

    time.sleep(1) 

    if client.is_connected():
        print(f"Publisher ({CLIENT_ID}): Publishing to '{topic_to_publish}', QoS={qos_level}, Payload='{message_payload}'")
        msg_info = client.publish(topic_to_publish, message_payload, qos=qos_level)
        
        if qos_level > 0:
            try:
                msg_info.wait_for_publish(timeout=5) 
                print(f"Publisher ({CLIENT_ID}): Publish confirmed by Paho for QoS {qos_level}.")
            except RuntimeError:
                print(f"Publisher ({CLIENT_ID}): Publish not confirmed by Paho within timeout for QoS {qos_level}.")
            except ValueError:
                print(f"Publisher ({CLIENT_ID}): ValueError on wait_for_publish for QoS {qos_level}.")

        time.sleep(2)
    else:
        print(f"Publisher ({CLIENT_ID}): Not connected. Cannot publish.")

    client.loop_stop()
    client.disconnect()
    print(f"Publisher ({CLIENT_ID}): Disconnected.")

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: python wireshark_test_publisher.py <topic> <payload> <qos>")
        print("Example (QoS 0): python wireshark_test_publisher.py test/qos0 'HelloQoS0' 0")
        print("Example (QoS 1): python wireshark_test_publisher.py test/qos1 'HelloQoS1' 1")
        print("Example (QoS 2): python wireshark_test_publisher.py test/qos2 'HelloQoS2' 2")
        sys.exit(1)

    topic = sys.argv[1]
    payload = sys.argv[2]
    qos = int(sys.argv[3])

    if qos not in [0, 1, 2]:
        print("Error: QoS level must be 0, 1, or 2.")
        sys.exit(1)

    publish_single_message(topic, payload, qos)
