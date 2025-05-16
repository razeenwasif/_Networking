import paho.mqtt.client as mqtt 
import time 
import datetime 
import sys 
import threading 
import csv 
from collections import defaultdict 

############################# Configurations ##################################

BROKER_ADDRESS = "localhost"
BROKER_PORT = 1883
REQUEST_TOPIC_QOS = "request/qos"
REQUEST_TOPIC_DELAY = "request/delay"
REQUEST_TOPIC_MESSAGESIZE = "request/messagesize"
REQUEST_TOPIC_INSTANCECOUNT = "request/instancecount"
REQUEST_TOPIC_GO = "request/go"
DATA_TOPIC_WILDCARD = "ctr/#"
SYS_TOPICS_TO_MONITOR = [
    "$SYS/broker/load/messages/received/1min",
    "$SYS/broker/load/messages/sent/1min",
    "$SYS/broker/clients/active",
    "$SYS/broker/messages/stored",
    "$SYS/broker/subscriptions/count"
]
TEST_DURATION_SECONDS = 30
OUTPUT_CSV_FILE = "mqtt_test_results.csv"

############################ Global Variables #################################

RECEIVED_PUBLISHER_MSGS = []
RECEIVED_SYS_MSGS = []
TEST_START_TIME = 0
DATA_COLLECTION_STOP_EVENT = threading.Event()

###############################################################################

def on_connect_analyzer(client, userdata, flags, rc, properties=None):
    """
    Callback invoked when the analyzer client successfully connects
    to the MQTT broker. 

    Args:
        client: The MQTT client instance 
        userdata: User-defined data passed to the client 
        flags: Response flags from the broker 
        rc: Connection result code (0 for success).
        properties: MQTTv5 properties
    """
    if rc == 0:
        print("Analyzer: Connected to MQTT Broker!")
    else:
        print(f"Analyzer: Failed to connect, return code {rc}")
        sys.exit(f"Analyzer could not connect to broker. Exiting. RC: {rc}")

def on_message_analyzer(client, userdata, msg):
    """
    Callback invoked when the analyzer client receives a message from the broker.
    It parses messages from publisher data topics ('ctr/#') and specified $SYS topics,
    storing them in global lists for later analysis.

    Args:
        client: The MQTT client instance.
        userdata: User-defined data 
        msg: An MQTTMessage object containing topic, payload, QoS, etc. 
    """
    global RECEIVED_PUBLISHER_MSGS, RECEIVED_SYS_MSGS 
    current_time_ms = int(time.time() * 1000)

    try:
        payload_str = msg.payload.decode()
    except UnicodeDecodeError:
        payload_str = "Error decoding payload (binary?)"
        print(f"Analyzer: Warning - UnicodeDecodeError for payload on topic {msg.topic}")

    if msg.topic.startswith("ctr/"):
        parts = msg.topic.split('/')
        payload_parts = payload_str.split(':', 2)

        if len(parts) == 5 and len(payload_parts) >= 2:
            try:
                message_data = {
                    "topic": msg.topic,
                    "publisher_instance_id": parts[1],
                    "original_qos": int(parts[2]),
                    "original_delay": int(parts[3]),
                    "original_message_size": int(parts[4]),
                    "payload_ctr": int(payload_parts[0]),
                    "payload_timestamp_sent": int(payload_parts[1]),
                    "payload_content_sample": payload_parts[2][:20] if len(payload_parts) > 2 else "",
                    "analyzer_timestamp_received": current_time_ms,
                    "analyzer_qos_subscribed": userdata.get("current_analyzer_qos", -1)
                }
                RECEIVED_PUBLISHER_MSGS.append(message_data)
            except ValueError:
                print(f"Analyzer: Error parsing publisher message data: Topic={msg.topic}, Payload={payload_str}")
        
        else:
            print(f"Analyzer: Received malformed publisher message: Topic={msg.topic}, Payload={payload_str}")

    elif msg.topic in SYS_TOPICS_TO_MONITOR:
        sys_data = {
            "topic": msg.topic,
            "payload": payload_str,
            "analyzer_timestamp_received": current_time_ms 
        }
        received_sys_messages.append(sys_data)

def publish_control_messages(client, pub_qos, pub_delay, pub_msg_size, pub_instance_count):
    """
    Publishes control parameters to the respective 'request/*' topics for publishers.
    These messages instruct publishers on how to behave for the upcoming test. All control messages 
    are sent with QoS 1 for reliability.

    Args:
        client: The MQTT client instance. 
        pub_qos (int): The QoS level for publishers to use.
        pub_delay (int): The delay between messages for publishers (in ms).
        pub_msg_size (int): The message payload size for publishers (in bytes)
        pub_instance_count (int): The number of publisher instances that should be active.
    """
    print(f"Analyzer: Publishing control: PubQoS={pub_qos}, Delay={pub_delay}, Size={pub_msg_size}, Instances={pub_instance_count}")
    client.publish(REQUEST_TOPIC_QOS, str(pub_qos), qos=1)
    client.publish(REQUEST_TOPIC_DELAY, str(pub_delay), qos=1)
    client.publish(REQUEST_TOPIC_MESSAGESIZE, str(pub_msg_size), qos=1)
    client.publish(REQUEST_TOPIC_INSTANCECOUNT, str(pub_instance_count), qos=1)
    time.sleep(0.5)

def trigger_publishers(client):
    """
    Sends the 'start' command to the 'request/go' topic.
    This signals active pubishers to begin their 30-second message burst.
    The command is sent with QoS 1.

    Args:
        client: The MQTT client instance.
    """
    print("Analyzer: Triggering publishers ('request/go start')")
    client.publish(REQUEST_TOPIC_GO, "start", qos=1)

def stop_publishers_command(client):
    """
    Sends a 'stop' command to the 'request/go' topic. 
    THis can be used to explicitly tell publishers to halt their bursts if needed.
    The command is sent with QoS 1.

    Args:
        client: The MQTT client instance.
    """
    print("Analyzer: Sending 'stop' command to publishers ('request/go stop')")
    client.publish(REQUEST_TOPIC_GO, "stop", qos=1)

def data_collection_thread_func(duration_seconds):
    """
    Runs for a specified duration, then sets an event to signal the end of the data 
    collection period for a test run. This function is intended to be run in a separate thread.

    Args:
        duration_seconds (int): The number of seconds to wait before signaling.
    """
    global DATA_COLLECTION_STOP_EVENT 
    DATA_COLLECTION_STOP_EVENT.clear()
    time.sleep(duration_seconds)
    DATA_COLLECTION_STOP_EVENT.set()
    print(f"Analyzer: {duration_seconds}s data collection period ended")

def calculate_stats(test_params):
    """
    Processes the globally collected 'RECEIVED_PUBLISHER_MSGS' and 'RECEIVED_SYS_MSGS'
    for the just-completed test run to calculate various performance metrics.

    Args:
        test_params (dict): A dictionary containing the parameters of the current test 
                            (e.g., analyzer_qos, pub_qos, pub_delay, etc.).
    Returns:
        dict: A dictionary where keys are metric names and values are the calculated 
              statistics for the current test run.
    """
    global RECEIVED_PUBLISHER_MSGS, RECEIVED_SYS_MSGS 

    total_msgs_received_by_analyzer = len(RECEIVED_PUBLISHER_MSGS)
    mean_total_rate_mps = total_msgs_received_by_analyzer / TEST_DURATION_SECONDS if TEST_DURATION_SECONDS > 0 else 0 

    publisher_data_grouped = defaultdict(list)
    for msg in RECEIVED_PUBLISHER_MSGS:
        publisher_data_grouped[msg["publisher_instance_id"]].append(msg)

    num_active_publishers_expected = test_params["pub_instance_count"]
    sum_loss_pct = 0 
    sum_outoforder_pct = 0 
    sum_duplicate_pct = 0 
    sum_avg_inter_msg_gap_ms = 0 
    sum_stddev_inter_msg_gap_ms = 0 
    publishers_reported_data_count = 0 

    for pub_id_str, pub_msgs in publisher_data_grouped.items():
        # only consider pubs that were supposed to be active for this test 
        try:
            if int(pub_id_str) > num_active_publishers_expected:
                continue 
        except ValueError:
            print(f"Analyzer: Warning - Non-integer publisher ID '{pub_id_str}' found in data.")
            continue 

        publishers_reported_data_count += 1 
        # sort messages by their original payload ctr 
        sorted_pub_msgs_by_ctr = sorted(pub_msgs, key=lambda x: x["payload_ctr"])

        actual_msgs_from_pub = len(sorted_pub_msgs_by_ctr)
        if actual_msgs_from_pub == 0:
            # if pub was expected to send but sent nothing, assume 100% loss 
            # for 0ms delay, if nothing is received, it could be 100% loss or pub issue 
            # if delay is fixed, expected number can be estimated 
            if test_params["pub_delay"] > 0:
                expected_at_delay = int(TEST_DURATION_SECONDS / (test_params["pub_delay"] / 1000.0))
                if expected_at_delay > 0: 
                    sum_loss_pct += 100 
            # else, if 0ms and 0 received, loss contribution will be based on 
            # max_ctr_seen below 
            continue 

        # Message loss
        # Based on unique ctrs received vs max ctr seen from this publisher 
        unique_ctrs_from_pub = sorted(list(set(m["payload_ctr"] for m in sorted_pub_msgs_by_ctr)))
        if not unique_ctrs_from_pub:
            loss_pct_this_pub = 100.0 if test_params["pub_delay"] > 0 else 0.0
        else:
            max_ctr_seen_this_pub = unique_ctrs_from_pub[-1]
            expected_based_on_max_ctr = max_ctr_seen_this_pub + 1 # assuming ctr start at 0 
            num_unique_received = len(unique_ctrs_from_pub)
            loss_count_for_this_pub = expected_based_on_max_ctr - num_unique_received 
            loss_pct_this_pub = (loss_count_for_this_pub / expected_based_on_max_ctr) * 100 if expected_based_on_max_ctr > 0 else 0 
        
        sum_loss_pct += loss_pct_this_pub 

        # Out of order messages 
        # sort by analyzer's reception time to see the order they arrived in 
        sorted_pub_msgs_by_arrival = sorted(pub_msgs, key=lambda x: x["analyzer_timestamp_received"])
        outoforder_count_this_pub = 0 
        if len(sorted_pub_msgs_by_arrival) > 1:
            # check if a message with a numerically smaller ctr arrived after one with bigger ctr 
            max_payload_ctr_seen_in_arrival_stream = -1
            for msg_in_arrival_order in sorted_pub_msgs_by_arrival:
                if msg_in_arrival_order["payload_ctr"] < max_payload_ctr_seen_in_arrival_stream:
                    outoforder_count_this_pub += 1 
                if msg_in_arrival_order["payload_ctr"] > max_payload_ctr_seen_in_arrival_stream:
                    max_payload_ctr_seen_in_arrival_stream = msg_in_arrival_order["payload_ctr"]
        
        outoforder_pct_this_pub = (outoforder_count_this_pub / actual_msgs_from_pub) * 100 if actual_msgs_from_pub > 0 else 0 
        sum_outoforder_pct += outoforder_pct_this_pub 

        # Duplicate messages 
        ctr_occurrences = defaultdict(int)
        for msg in sorted_pub_messages_by_ctr:
            ctr_occurrences[msg["payload_ctr"]] += 1 
        duplicate_count_this_pub = 0 

        for count_val in ctr_occurrences.values():
            if count_val > 1:
                duplicate_count_this_pub += (count_val - 1)

        duplicate_pct_this_pub = (duplicate_count_this_pub / actual_msgs_from_pub) * 100 if actual_msgs_from_pub > 0 else 0 
        sum_duplicate_pct += duplicate_pct_this_pub 

        # Inter-Message Gap (Timestamp diff b/w consecutive msgs)
        inter_message_gaps_this_pub = [] 
        # store first arrival time for each unique ctr 
        arrival_times_for_unique_ctrs = {}
        for msg in sorted_pub_msgs_by_arrival:
            if msg["payload_ctr"] not in arrival_times_for_unique_ctrs:
                arrival_times_for_unique_ctrs[msg["payload_ctr"]] = msg["analyzer_timestamp_received"]

        # iterate through the unique ctrs in their numerical order 
        for i in range(len(unique_ctrs_from_pub) - 1):
            current_ctr = unique_ctrs_from_pub[i]
            next_ctr = unique_ctrs_from_pub[i+1]
            if next_ctr == current_ctr + 1: # check if consecutive 
                # ensure both counters were received and have timestamps 
                if current_ctr in arrival_times_for_unique_ctrs and next_ctr in arrival_times_for_unique_ctrs:
                    gap = arrival_times_for_unique_ctrs[next_ctr] - arrival_times_for_unique_ctrs[current_ctr]
                    inter_message_gaps_this_pub.append(gap)

        avg_gap_ms_this_pub = 0 
        stddev_gap_ms_this_pub = 0 
        if inter_message_gaps_this_pub:
            avg_gap_ms_this_pub = sum(inter_message_gaps_this_pub) / len(inter_message_gaps_this_pub)
            if len(inter_message_gaps_this_pub) > 1:
                variance = sum([(g - avg_gap_ms_this_pub) ** 2 for g in inter_message_gaps_this_pub]) / len(inter_message_gaps_this_pub)
                stddev_gap_ms_this_pub = variance ** 0.5 
        sum_avg_inter_msg_gap_ms += avg_gap_ms_this_pub 
        sum_stddev_inter_msg_gap_ms += stddev_gap_ms_this_pub 

    # Averaging per-publisher statistics -------------------------------------- 

    avg_loss_pct_overall = sum_loss_pct / publishers_reported_data_count if publishers_reported_data_count > 0 else (100 if num_active_publishers_expected > 0 else 0)
    avg_outoforder_pct_overall = sum_outoforder_pct / publishers_reported_data_count if publishers_reported_data_count > 0 else 0 
    avg_dup_pct_overall = sum_duplicate_pct / publishers_reported_data_count if publishers_reported_data_count > 0 else 0 
    avg_inter_msg_gap_ms_overall = sum_avg_inter_msg_gap_ms / publishers_reported_data_count if publishers_reported_data_count > 0 else 0 
    avg_stddev_inter_msg_gap_ms_overall = sum_stddev_inter_msg_gap_ms / publishers_reported_data_count if publishers_reported_data_count > 0 else 0 

    # Process $SYS topics -----------------------------------------------------

    # store last seen val for each monitored $SYS topic during the test period
    processed_sys_metrics = {}
    sys_data_by_topic = defaultdict(list)
    for sys_msg in received_sys_messages:
        sys_data_by_topic[sys_msg["topic"]].append(sys_msg["payload"])

    for topic_key in SYS_TOPICS_TO_MONITOR:
        clean_key = topic_key.replace("$SYS/broker/", "").replace("/", "_")
        processed_sys_metrics[f"SYS_{clean_key}_last"] = sys_data_by_topic[topic_key][-1] if sys_data_by_topic[topic_key] else "N/A"

    results = {
        "Test_Run_Timestamp": datetime.datetime.now().isoformat(),
        "Analyzer_sub_QoS": test_params["analyzer_qos"],
        "Publisher_pub_QoS": test_params["pub_qos"],
        "Publisher_delay_ms": test_params["pub_delay"],
        "Publisher_msg_size_bytes": test_params["pub_msg_size"],
        "Publisher_instance_count_cfg": test_params["pub_instance_count"],
        "Total_msgs_received_by_analyzer": total_msgs_received_by_analyzer,
        "Mean_total_rate_mps_analyzer": round(mean_total_rate_mps, 3),
        "Avg_loss_pct_per_active_pub": round(avg_loss_pct_overall, 3),
        "Avg_outoforder_pct_per_active_pub": round(avg_outoforder_pct_overall, 3),
        "Avg_dup_pct_per_active_pub": round(avg_dup_pct_overall, 3),
        "Avg_inter_msg_gap_ms_per_active_pub": round(avg_inter_msg_gap_ms_overall, 3),
        "Avg_stddev_inter_msg_gap_ms_per_active_pub": round(avg_stddev_inter_msg_gap_ms_overall, 3),
        **processed_sys_metrics 
    }
    return results 

def write_results_to_csv(results_dict, is_first_write):
    """
    Appends a dict of results (one row) to the specified CSV file.
    If it's the first write op to a new/empty file, it writes the header row. 

    Args:
        results_dict (dict): The dictionary containing data for one test run 
        is_first_write (bool): True if this is the first time writing to the CSV 
    """
    try:
        fieldnames = results_dict.keys()
        file_exists = False 
        try:
            with open(OUTPUT_CSV_FILE, mode='r') as f:
                if f.read(1): file_exists = True 
        except FileNotFoundError:
            file_exists = False 

        with open(OUTPUT_CSV_FILE, mode='a', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists or is_first_write and csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow(results_dict)
    except IOError as e:
        print(f"Analyzer: Error writing to CSV file '{OUTPUT_CSV_FILE}': {e}")
    except Exception as e:
        print(f"Analyzer: Unexpected error occured during CSV writing: {e}")

def main_analyzer():
    """
    The main function for the analyzer.
    1. Defines the parameter space for all test combinations
    2. Connects to the MQTT broker 
    3. Iterates through each test combination:
        a. Sets up subscriptions with the correct Analyzer QoS.
        b. Resets data collectors 
        c. Publishes control messages to configure the publishers.
        d. Starts a data collection timer thread. 
        e. Triggers the publishers to start sending data.
        f. Waits for the data collection period to end. 
        g. Calculates performance statistics from the collected data.
        h. Writes the statistics to a CSV file 
    4. Disconnects from the broker after all tests are complete.
    """
    global RECEIVED_PUBLISHER_MSGS, RECEIVED_SYS_MSGS, TEST_START_TIME, DATA_COLLECTION_STOP_EVENT 

    pub_qos_levels = [0, 1, 2]
    pub_delay_ms = [0, 100]
    pub_msg_sizes_bytes = [0, 1000, 4000]
    pub_instance_counts = [1, 5, 10]
    analyzer_subscription_qos_levels = [0, 1, 2]

    # Ensure client ID is unique if multiple analyzers run against the same broker
    analyzer_client_id = f"analyzer_client_{int(time.time())}"
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=analyzer_client_id)
    client.on_connect = on_connect_analyzer 
    client.on_message = on_message_analyzer 

    try:
        client.connect(BROKER_ADDRESS, BROKER_PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"Analyzer: Error connecting to broker: {e}. Exiting")
        return 

    # Wait for connection to establish 
    connection_timeout = 10 
    wait_start_time = time.time()
    while not client.is_connected() and (time.time() - wait_start_time) < connection_timeout:
        print("Analyzer: Waiting for initial connection")
        time.sleep(1)

    if not client.is_connected():
        print("Analyzer: Failed to connect to broker after timeout. Exiting")
        client.loop_stop()
        return 

    test_run_ctr = 0 
    is_first_csv_write = True 

    for analyzer_qos_level in analyzer_subscription_qos_levels:
        client.user_data_set({"current_analyzer_qos": analyzer_qos_level})
        print(f"\nAnalyzer: Setting up subscriptions for Analyzer QoS = {analyzer_qos_level}")
        # Unsub from all relevant topics first to ensure QoS change takes effect 
        client.unsubscribe(DATA_TOPIC_WILDCARD)
        for sys_topic in SYS_TOPICS_TO_MONITOR:
            client.unsubscribe(sys_topic)
        time.sleep(1) 

        # Subscribe with the new Analyzer QoS 
        client.subscribe(DATA_TOPIC_WILDCARD, qos=analyzer_qos_level)
        for sys_topic in SYS_TOPICS_TO_MONITOR:
            client.subscribe(sys_topic, qos=analyzer_qos_level)
        time.sleep(1)

        for pub_qos_val in pub_qos_levels:
            for pub_delay_val in pub_delay_ms:
                for pub_msg_size_val in pub_msg_sizes_bytes:
                    for pub_instance_count_val in pub_instance_counts:
                        test_run_ctr += 1 
                        print(f"\n---- Starting test {test_run_ctr}/162 ----")
                        current_test_params = {
                            "analyzer_qos": analyzer_qos_level, 
                            "pub_qos": pub_qos_val,
                            "pub_delay": pub_delay_val, 
                            "pub_msg_size": pub_msg_size_val, 
                            "pub_instance_count": pub_instance_count_val 
                        }
                        print(f"Parameters: {current_test_params}")

                        RECEIVED_PUBLISHER_MSGS.clear()
                        RECEIVED_SYS_MSGS.clear()
                        DATA_COLLECTION_STOP_EVENT.clear()

                        publish_control_messages(client, pub_qos_val, pub_delay_val, pub_msg_size_val, pub_instance_count_val)
                        
                        print(f"Analyzer: Starting {TEST_DURATION_SECONDS}s data collection...")
                        TEST_START_TIME = time.time()

                        collection_timer_thread = threading.Thread(target=data_collection_thread_func, args=(TEST_DURATION_SECONDS,))
                        collection_timer_thread.start()

                        trigger_publishers(client)
                        collection_timer_thread.join()

                        print("Analyzer: Calculating stats...")
                        calculated_stats = calculate_stats(current_test_params)
                        print(f"Analyzer: Results for test {test_run_ctr}:{calculated_stats}")

                        write_results_to_csv(calculated_stats, is_first_write=is_first_csv_write)
                        if is_first_csv_write:
                            is_first_csv_write = False 

                        print(f"---- Test {test_run_ctr} Complete ----")
                        time.sleep(3)

    print("\n==== All 162 Tests Complete ====")
    print(f"Results saved to {OUTPUT_CSV_FILE}")
    client.loop_stop()
    client.disconnect()
    print("Analyzer: Disconnected and shutdown")

if __name__ == '__main__':
    main_analyzer() 




# --- TODO List ---
# 1.  [CRITICAL] `calculate_statistics`: Thoroughly test and validate all metric calculations against expected behaviors and small, controlled test cases.
#     *   Loss: "Expected messages" for 0ms delay needs robust definition. Current logic uses max counter seen.
#     *   Out-of-Order: The current definition ("smaller number after a larger number" in arrival stream) should be double-checked against assignment intent.
#     *   Inter-Message Gap: Ensure it's strictly for *consecutive* payload counters as per assignment.
# 2.  `calculate_statistics`: $SYS data processing is basic (last value). Enhance if more sophisticated analysis (e.g., average, min/max over test period) is needed for the report.
# 3.  Broker Behavior for Analyser QoS Change: The assignment mentions analyser client disconnect/reconnect might be needed for subscription QoS changes.
#     Current code only re-subscribes. Test this with your chosen broker. If issues, implement full disconnect/reconnect of the analyser client
#     when `analyser_qos_level` changes in `main_analyser`.
# 4.  Error Handling: Add more specific error handling within `calculate_statistics` if data is malformed or missing.
# 5.  Configuration: Consider moving `SYS_TOPICS_TO_MONITOR` and other configs to a separate `config.py` or JSON file for easier modification.
# 6.  Resource Management: Ensure threads are always joined and resources cleaned up, especially on unexpected exits. (Current version is okay, but review).
# 7.  Clarity of Output: Refine print statements for better real-time monitoring during the long test sequence.
# 8.  CSV Field Order: For Python < 3.7, `dict.keys()` order is not guaranteed. If compatibility is needed, explicitly define `fieldnames` for `csv.DictWriter`
#     using a list to ensure consistent column order in the CSV. (Python 3.7+ maintains insertion order for dicts).
# 9.  Wireshark: This script does not perform Wireshark captures. This is a manual task for the report, focusing on QoS handshakes.
# 10. Performance of Analyser: For very high message rates, the single `on_message_analyser` callback might become a bottleneck.
#     For this assignment's scope, it's likely fine, but be aware if issues arise with extremely fast 0ms delay tests.
#     (Python's GIL means true parallelism for CPU-bound tasks in one process is limited).
# 11. Publisher `stop` command: The `stop_publishers_command(client)` is currently commented out. If publishers don't reliably stop after 30s
#     on their own (e.g., due to timing drift or implementation), uncommenting this might be useful to signal them to cease sending before the next test begins.





