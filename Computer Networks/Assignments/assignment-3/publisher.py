import paho.mqtt.client as mqtt 
import time 
import sys
import threading # for publishing burst 

############################### Congifuration #################################
# load from config.py 
BROKER_ADDRESS = "localhost" # or broker IP address 
BROKER_PORT = 1883 
REQUEST_TOPIC_QOS = "request/qos"
REQUEST_TOPIC_DELAY = "request/delay"
REQUEST_TOPIC_MESSAGESIZE = "request/messagesize"
REQUEST_TOPIC_INSTANCECOUNT = "request/instancecount"
REQUEST_TOPIC_GO = "request/go"
DATA_TOPIC_PREFIX = "counter"
RECONNECT_DELAY = 5
###############################################################################

# Global Variables 
CURRENT_QOS = 0
CURRENT_DELAY = 100 # ms 
CURRENT_MESSAGE_SIZE = 0 # bytes 
CURRENT_INSTANCE_COUNT = 1 
PUBLISHER_ID = "pub-01"
IS_ACTIVE = False 
PUBLISHING_THREAD = None 
STOP_PUBLISHING_EVENT = threading.Event()
# lock to prevent multiple reconnection attempts from running simultaneously 
RECONNECT_LOCK = threading.Lock()
IS_RECONNECTING = False
CLI_PUBLISHER_ID = None # set by cli 

########################### MQTT Callback Functions ###########################
def on_connect(client, userdata, flags, rc, properties=None):
    """
    Callback for when the client receives a CONNACK response from the server.
    
    Args:
        client: The client instance for this callback 
        userdata: The private user data as set in Client() or user_data_set()
        flags: response flags sent by the broker. 
        rc: The connection result.
            0: Connection successful 
            1: Connection refused - incorrect protocol version 
            2: Connection refused - invalid client identifier
            3: Connection refused - server unavailable 
            4: Connection refused - bad username or password 
            5: Connection refused - not authorised 
            6-255: Currently unused.
        properties: The MQTTv5 properties received with CONNACK.
    """
    global IS_RECONNECTING, CLI_CLI_PUBLISHER_ID
    if rc == 0:
        print(f"{CLI_PUBLISHER_ID}: Connected to MQTT Broker")
        IS_RECONNECTING = False # reset on successful connect 
        # resub on (re)connect 
        client.subscribe([(REQUEST_TOPIC_QOS, 0),
                          (REQUEST_TOPIC_DELAY, 0),
                          (REQUEST_TOPIC_MESSAGESIZE, 0),
                          (REQUEST_TOPIC_INSTANCECOUNT, 0),
                          (REQUEST_TOPIC_GO, 0)])
        print(f"{CLI_PUBLISHER_ID}: Subscribed to request topics.")
    else:
        print(f"{CLI_PUBLISHER_ID}: Failed to connect, return code {rc}")
        if not IS_RECONNECTING:
            attempt_reconnect(client)

def on_disconnect(client, userdata, flags, rc, properties=None):
    """
    Callback for when the client disconnects from the broker.

    Args:
        client: The client instance for this callback.
        userdata: The private user data as set in Client() or user_data_set()
        rc: The disconnection result. If MQTT_ERR_SUCCESS (0), it was a planned disconnect 
        properties: The MQTTv5 properties received with DISCONNECT (if any).
    """
    global IS_RECONNECTING, CLI_PUBLISHER_ID
    actual_paho_rc = rc # paho client's rtn code for disconnect event 
    broker_reason_code = 'N/A'
    disconnect_source = 'unknown'

    if isinstance(flags, int): # fallback for oldstyle
        print(f"{CLI_PUBLISHER_ID}: Disconnected (legacy callback interpretation). RC from Paho: {flags}")
        actual_paho_rc = flags 
    else: # Normal Paho MQTT v2.x 
        if hasattr(flags, 'reason_code'):
            broker_reason_code = flags.reason_code 
        if hasattr(flags, 'is_client_disconnect') and flags.is_client_disconnect:
            disconnect_source = "client-initiated"
        elif broker_reason_code != 'N/A':
            disconnect_source = "broker-initiated"
        else:
            disconnect_source = "network/unexpected"

    print(f"{CLI_PUBLISHER_ID}: Disconnected. Source: {disconnect_source}. Paho RC: {actual_paho_rc}. Broker Reason Code: {broker_reason_code}.")

    should_reconnect = False 
    if actual_paho_rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"{CLI_PUBLISHER_ID}: Paho RC indicates an issue ({actual_paho_rc}). Will attempt reconnect.")
        should_reconnect = True 
    elif disconnect_source == "broker-initiated":
        print(f"{CLI_PUBLISHER_ID}: Broker initiated disconnect (Reason: {broker_reason_code}). Will attempt reconnect.")
        should_reconnect = True 
    elif disconnect_source == "network/unexpected":
        print(f"{CLI_PUBLISHER_ID}: Network/unexpected disconnect. Will attempt reconnect.")
        should_reconnect = True 

    if should_reconnect:
        if not IS_RECONNECTING:
            print(f"{CLI_PUBLISHER_ID}: Triggering reconnection logic...")
            attempt_reconnect(client)
        else:
            print(f"{CLI_PUBLISHER_ID}: Reconnection attempt already in progress.")
    else:
        print(f"{CLI_PUBLISHER_ID}: Clean disconnect, no reconnection attempt needed.")

def attempt_reconnect(client):
    """
    Attempts to reconnect to the broker with a delay 
    This function is designed to be called when a disconnection is detected.

    Args:
        client: The MQTT client instance.
    """
    global IS_RECONNECTING
    if RECONNECT_LOCK.acquire(blocking=False): # attempt to acquire lock w/o blocking
        IS_RECONNECTING = True 
        try:
            print(f"{CLI_PUBLISHER_ID}: Reconnection attempt in {RECONNECT_DELAY} seconds.")
            time.sleep(RECONNECT_DELAY)
            print(f"{CLI_PUBLISHER_ID}: Attempting to reconnect...")

            try:
                client.reconnect()
            except Exception as e:
                print(f"{CLI_PUBLISHER_ID}: Error during reconnect attempt: {e}")
                IS_RECONNECTING = False # allow more attempts 
        finally:
            if not client.is_connected():
                IS_RECONNECTING = False 
            RECONNECT_LOCK.release()
    else:
        print(f"{CLI_PUBLISHER_ID}: Reconnection attempt already in progress")

def on_message(client, userdata, msg):
    """
    Callback for when a PUBLISH message is received from the server.

    Args:
        client: The client instance for this callback 
        userdata: The private user data as set in Client() or user_data_set()
        msg: An MQTTMessage instance. It has members topic, payload, qos, retain.
    """
    global CURRENT_QOS, CURRENT_DELAY, CURRENT_MESSAGE_SIZE, CURRENT_INSTANCE_COUNT, IS_ACTIVE
    global PUBLISHING_THREAD, STOP_PUBLISHING_EVENT 

    payload = msg.payload.decode()
    print(f"{CLI_PUBLISHER_ID}: Received message on {msg.topic}: {payload}")

    if msg.topic == REQUEST_TOPIC_QOS:
        try:
            CURRENT_QOS = int(payload)
            if CURRENT_QOS not in [0, 1, 2]:
                print(f"{CLI_PUBLISHER_ID}: Invalid QoS value received: {CURRENT_QOS}. Defaulting to 0.")
                CURRENT_QOS = 0 
            else:
                print(f"{CLI_PUBLISHER_ID}: QoS set to {CURRENT_QOS}")
        except ValueError:
            print(f"{CLI_PUBLISHER_ID}: Invalid QoS payload: {payload}")

    elif msg.topic == REQUEST_TOPIC_DELAY:
        try:
            CURRENT_DELAY = int(payload)
            if CURRENT_DELAY < 0:
                print(f"{CLI_PUBLISHER_ID}: Invalid delay value received: {CURRENT_DELAY}. Defaulting to 0.")
                CURRENT_DELAY = 0 
            else:
                print(f"{CLI_PUBLISHER_ID}: Delay set to {CURRENT_DELAY}ms")
        except ValueError:
            print(f"{CLI_PUBLISHER_ID}: Invalid delay payload: {payload}")

    elif msg.topic == REQUEST_TOPIC_MESSAGESIZE:
        try:
            CURRENT_MESSAGE_SIZE = int(payload)
            if CURRENT_MESSAGE_SIZE < 0:
                print(f"{CLI_PUBLISHER_ID}: Invalid message size received: {CURRENT_MESSAGE_SIZE}. Defaulting to 0")
                CURRENT_MESSAGE_SIZE = 0 
            else:
                print(f"{CLI_PUBLISHER_ID}: Message size set to {CURRENT_MESSAGE_SIZE} bytes")
        except ValueError:
            print(f"{CLI_PUBLISHER_ID}: Invalid message size payload: {payload}")

    elif msg.topic == REQUEST_TOPIC_INSTANCECOUNT:
        try: 
            CURRENT_INSTANCE_COUNT = int(payload)
            print(f"{CLI_PUBLISHER_ID}: Instance count set to {CURRENT_INSTANCE_COUNT}")
            # Determine if this pub instance should be active 
            instance_number = int(CLI_PUBLISHER_ID.split('-')[1])
            if 1 <= instance_number <= CURRENT_INSTANCE_COUNT:
                if not IS_ACTIVE:
                    print(f"{CLI_PUBLISHER_ID} is now active (Instance count: {CURRENT_INSTANCE_COUNT})")
                IS_ACTIVE = True 
            else:
                if IS_ACTIVE:
                    print(f"{CLI_PUBLISHER_ID} is now inactive (Instance count: {CURRENT_INSTANCE_COUNT})")
                IS_ACTIVE = False 
                if PUBLISHING_THREAD and PUBLISHING_THREAD.is_alive():
                    print(f"{CLI_PUBLISHER_ID}: Became inactive. Signaling current publishing burst to stop")
                    STOP_PUBLISHING_EVENT.set()
        except ValueError:
            print(f"{CLI_PUBLISHER_ID}: Invalid instance count payload: {payload}")
        except (IndexError, TypeError):
            print(f"{CLI_PUBLISHER_ID}: Could not parse instance number from publisher ID '{CLI_PUBLISHER_ID}'")
            IS_ACTIVE = False
            if PUBLISHING_THREAD and PUBLISHING_THREAD.is_alive():
                print(f"{CLI_PUBLISHER_ID}: Error parsing ID. Signaling current publishing burst to stop.")
                STOP_PUBLISHING_EVENT.set()

    elif msg.topic == REQUEST_TOPIC_GO:
        if payload.lower() == "start": 
            if IS_ACTIVE:
                if PUBLISHING_THREAD is None or not PUBLISHING_THREAD.is_alive():
                    print(f"{CLI_PUBLISHER_ID}: 'Go' signal received. Starting publishing burst")
                    # clear event before starting 
                    STOP_PUBLISHING_EVENT.clear() 
                    PUBLISHING_THREAD = threading.Thread(target=publish_burst, args=(client,))
                    PUBLISHING_THREAD.start() 
                else:
                    print(f"{CLI_PUBLISHER_ID}: Publishing already in progress.")
            else:
                print(f"{CLI_PUBLISHER_ID}: 'Go' signal received, but pub inactive.")

        elif payload.lower() == "stop": # remote stop 
            print(f"{CLI_PUBLISHER_ID}: 'Stop' signal received.")
            if PUBLISHING_THREAD and PUBLISHING_THREAD.is_alive():
                STOP_PUBLISHING_EVENT.set()

def publish_burst(client):
    """
    Manages the 30-second burst of message publishing. 
    This function is intended to be run in a separate thread. It sends messages at a rate 
    determined by 'CURRENT_DELAY' with a payload size of 'CURRENT_MESSAGE_SIZE' and QoS level 
    'CURRENT_QOS'.

    Args:
        client: The MQTT client instance used for publishing.
    """
    global CURRENT_QOS, CURRENT_DELAY, CURRENT_MESSAGE_SIZE, CLI_PUBLISHER_ID, STOP_PUBLISHING_EVENT 
    print(f"{CLI_PUBLISHER_ID}: Starting 30s publish burst. QoS={CURRENT_QOS}, Delay={CURRENT_DELAY}ms, Size={CURRENT_MESSAGE_SIZE}")

    start_time = time.time()
    message_counter = 0 
    payload_string = 'x' * CURRENT_MESSAGE_SIZE 
    topic_instance_id = CLI_PUBLISHER_ID.split('-')[1] 
    publish_topic = f"{DATA_TOPIC_PREFIX}/{topic_instance_id}/{CURRENT_QOS}/{CURRENT_DELAY}/{CURRENT_MESSAGE_SIZE}"

    while time.time() - start_time < 30:
        if STOP_PUBLISHING_EVENT.is_set():
            print(f"{CLI_PUBLISHER_ID}: Publishing burst interrupted by stop event.")
            break 

        timestamp_ms = int(time.time() * 1000)
        message = f"{message_counter}:{timestamp_ms}:{payload_string}"

        result = client.publish(publish_topic, message, qos=CURRENT_QOS)

        message_counter += 1
        # delay of 0 will loop as fast as possible
        if CURRENT_DELAY > 0:
            time.sleep(CURRENT_DELAY / 1000.0)

    print(f"{CLI_PUBLISHER_ID}: Finished publishing burst. Sent {message_counter} messages in approx 30 seconds")
    # Goes back to listening 

def main():
    """
    Main function to initialize and run the MQTT publisher client.
    It parses command-line arguments for the publisher ID, sets up the MQTT client, 
    connects to the broker, and starts the client's network loop.
    """
    global CLI_PUBLISHER_ID 

    if len(sys.argv) < 2:
        print("Usage: python publisher.py <CLI_PUBLISHER_ID>")
        print("Example: python publisher.py pub-01")
        sys.exit(1)

    CLI_PUBLISHER_ID = sys.argv[1]
    instance_number_try = 0 

    try:
        instance_number_try = int(CLI_PUBLISHER_ID.split('-')[1])
        if not (1 <= instance_number_try <= 10):
            raise ValueError("Instance number out of range 1-10")
    except (IndexError, ValueError) as e:
        print(f"Error: Publisher ID must be in the format 'pub-XX' where XX is a number from 01 to 10. Got: {CLI_PUBLISHER_ID}")
        print(e)
        sys.exit(1)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=CLI_PUBLISHER_ID) 

    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect 

    try:
        print(f"{CLI_PUBLISHER_ID}: Attempting to connect to broker {BROKER_ADDRESS}:{BROKER_PORT}")
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
    except Exception as e:
        print(f"{CLI_PUBLISHER_ID}: Error connecting to broker: {e}")
        sys.exit(1)

    # Start the MQTT network loop 
    # loop_start() runs the loop in a background threading
    # loop_forever() blocks until client.disconnect() is called 

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"{CLI_PUBLISHER_ID}: Exiting due to KeyboardInterrupt")
    finally: 
        if PUBLISHING_THREAD and PUBLISHING_THREAD.is_alive():
            STOP_PUBLISHING_EVENT.set()
            PUBLISHING_THREAD.join(timeout=5) 
        client.disconnect()
        print(f"{CLI_PUBLISHER_ID}: Disconnected and shutdown")

if __name__ == '__main__':
    main()

