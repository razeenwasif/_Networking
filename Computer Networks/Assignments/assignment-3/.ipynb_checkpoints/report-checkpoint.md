Razeen Wasif
u7283652
COMP3310
May 11, 2025

# Abstract 

This report details an experimental investigation into the performance characteristics of the Message Queuing Telemetry Transport (MQTT) protocol. A custom testing suite, comprising configurable Python based MQTT publishers and an analyzer, was developed to systematically evaluate the protocol's behaviour across a range of parameters. These parameters included different Quality of Service (QoS) levels for publishers and the analyzer, message inter-send delays, message payload sizes, and varying numbers of concurrently active publisher instances. Key performance metrics such as throughput, message loss, out-of-order message delivery, message duplication, and inter-message arrival gaps were measured. Additionally, broker-side statistics, obtained via MQTT $SYS topics, were monitored to correlate application-level performance with broker load. The study aims to provide insights into MQTT's scalability, reliability, and the trade-offs associated with its different operational modes, particularly highlighting system limitations encountered under extreme load conditions.

# Methodology 
## Setup
- **MQTT Broker:** Mosquitto MQTT Broker was deployed on a local machine (EndeavourOS, Intel Core i7-7660U, 16GB RAM).
- **Publisher Clients (`publisher.py`):** Ten instances of MQTT publisher client were developed using the Paho-MQTT library. Each publisher was uniquely identifiable (`pub-01` to `pub-10`) and capable of:
    - Subscribing to control topics (`request/qos`, `request/delay`, `request/messagesize`, `request/instancecount`, `request/go`) to receive test parameters from the analyzer.
    - Publishing messages for a fixed duration of 30 seconds per test run.
    - Constructing messages in the format `counter:timestamp:payload`.
    - Publishing to dynamically generated topics: `counter/<instance_id>/<pub_qos>/<pub_delay>/<message_size>`.
    - Operating according to the received parameters regarding QoS, inter-message delay, payload size, and active/inactive state based on `instancecount`.
    - Implementing reconnection logic for broker disconnections.

- **Analyzer Client (`analyzer.py`):** A MQTT analyzer client was developed using Paho-MQTT to:
    - Orchestrate the 162 distinct test runs by publishing control messages to the publishers.
    - Subscribe to publisher data topics (`counter/#`) with varying analyzer-side QoS levels.
    - Subscribe to selected MQTT $SYS topics (e.g., `$SYS/broker/load/messages/sent/1min`, `$SYS/broker/clients/active`) to monitor broker status.
    - Collect all received publisher and $SYS messages during each 30-second test period.
    - Calculate performance statistics after each test run.
    - Log all test parameters and calculated statistics to a CSV file (mqtt_test_results.csv)

## Test Parameters
The following parameters were systematically varied to create 162 unique test combinations:
- **Analyzer Subscription QoS:** 0, 1, 2 
- **Publisher-to-Broker QoS:** 0, 1, 2
- **Inter-Message Delay (Publisher):** 0ms, 100ms
- **Message Payload Size (Publisher):** 0 bytes, 1000 bytes, 4000 bytes (string of 'x' chars)
- **Number of Active Publisher Instances:** 1, 5, 10
Each test combination was run for 30 seconds of active message publishing. A brief pause was introduced between tests.

## Performance Metrics Collected
The analyzer calculated the following metrics for each test run:
- **Total Messages Received by Analyzer:** Absolute count of messages from publishers.
- **Mean Total Rate (messages/second):** Total messages received / test duration.
- **Average Message Loss Percentage (per active publisher):** Calculated based on the sequence of received message counters versus the maximum counter seen from each publisher.
  ```python
  Loss = (expected_by_max_counter - unique_received) / expected_by_max_counter
  ```
- **Average Out-of-Order Message Percentage (per active publisher):** Percentage of messages received with a payload counter smaller than a previously received message's counter from the same publisher (when sorted by analyzer arrival time).
- **Average Duplicate Message Percentage per active publisher):** Percentage of messages received with the same payload counter from the same publisher, beyond the first instance.
- **Average Inter-Message Gap (ms, per active publisher):** Mean time difference between the analyzer's reception of numerically consecutive message counters from the same publisher.
- **Average Standard Deviation of Inter-Message Gap (ms, per active publisher):** Standard deviation of the above gaps.
- **Selected $SYS Topic Values:** Last known values for topics like broker message load, active clients, and subscription counts during the test period.

## Wireshark Analysis of QoS Levels
Packet captures were performed using Wireshark (filtered for MQTT traffic) to examine the handshake and message exchange mechanisms for representative examples of publisher-analyzer communications at QoS 0, QoS 1, QoS 2.

# Results and Analysis
## Wireshark Analysis of MQTT QoS Handshakes

- **QoS 0:**
    -  (-- insert screenshots --)
    -  **Observation:** The publisher sends a PUBLISH message to the broker. The broker, in turn, sends a PUBLISH message to the subscribed analyzer. No explicit acknowledgments are involved at the MQTT level for the message derlivery itself. This results in the lowest overhead but offers no guarantee of delivery.

- **QoS 1:**
    -  (-- insert screenshots --)
    -  **Observation:**
          1. Publisher sends PUBLISH (Packet ID: P1) to Broker.
          2. Broker receives, stores, and sends PUBACK (Packet ID: P1) back to Publisher.
          3. Broker sends PUBLISH (Packet ID: B1, potentially different from P1) to Analyzer.
          4. Analyzer receives and sends PUBACK (Packet ID: B1) back to Broker.
    - This ensures the message is delivered at least once. If acknowledgements are lost, retransmissions (with DUP flag set) can occur, potentially leading to duplicate message delivery at the application layer if not handled by the subscriber.

- **QoS 2:**
    -  (-- insert screenshots --)
    -  **Observation:** A four-part handshake ensures exactly-once delivery semantics:
          1. Publisher sends PUBLISH (Packet ID: P1) to Broker.
          2. Broker receives, stores, and sends PUBREC (Publish Received, Packet ID: P1) to Publisher.
          3. Publisher receives PUBREC, discards its copy of the original PUBLISH, stores P1, and sends PUBREL (Publish Release, Packet ID: P1) to Broker.
          4. Broker receives PUBREL, delivers the message to the Analyzer (this internal delivery to the analyzer also involves a QoS 2 handshake if the analyzer subscribed at QoS 2), discards its stored state for P1, and sends PUBCOMP (Publisher Complete, Packet ID: P1) to Publisher.
          5. Publisher receives PUBCOMP and discards its stored state for P1.
    - This is the most reliable but highest overhead QoS level, designed to prevent both message loss and duplication.

# Implications for Message Duplication and Order:
- QoS 0: Messages can be lost or arrive out of order. Duplicates are not an inherent part of QoS 0 itself but could occur due to network retransmissions below MQTT.
- QoS 1: Guarantees delivery but allows for duplicates if acknowledgements are lost and messages are re-sent. Order is not guaranteed relative to other messages.
- QoS 2: Guarantees delivery exactly once and, within a single publisher's stream of QoS 2 messages to a specific topic, helps maintain order if the broker processes them sequentially for that client.

# Circumstances for Choosing Each QoS Level:
- QoS 0: Suitable for telemetry data where occasional loss is acceptable, and low overhead/power consumption is critical (e.g., frequent non-critical sensor readings).
- QoS 1: Use when message delivery is important, and the application can tolerate or handle duplicate messages (e.g., commands that are idempotent, status updates where the latest one matters).
- QoS 2: Essential for critical messages where neither loss nor duplication can be tolerated (e.g., billing information, transactional commands).

# System Performance under Various Conditions
The full dataset comprises of 168 test runs. However, a significant observation was made during tests involving `Publisher_delay_ms = 0` combined with multiple `Publisher_instance_count_cfg` (5 or 10) and larger `Publisher_msg_size_bytes` (1000 or 4000). Under these high-load conditions, system RAM usage reached its capacity (approximately 14G / 15.5GB). This led to test failures where the analyzer recorded zero messages received and 100% message loss, likely due to publisher processes or the MQTT broker becoming unresponsive or being terminated by the operating system's Out-of-Memory killer. 

Consequently, the analysis below primarily focuses on data from 15 tests where message reception was consistently observed and not dominated by system RAM limitations. Data from tests that induced system failure are also discussed as they highlight the operational boundaries of the test environment. 

## Throughput (Mean Messages per Second Received by Analyzer)
Throughput was measured as the number of messages successfully received by the analyser per second.
- **Effect of Publisher Delay:**
    - Tests with `Publisher_delay_ms = 100ms` resulted in significantly lower and more stable throughput compared to `Publisher_delay_ms = 0ms`. For instance, with Analyzer QoS 0, Publisher QoS 0, 0 byte message size, and 1 publisher instance, the throughput was consistently around **9.97 mps** (e.g., rows 4, 6 in the dataset). This scaled with active publishers; with 3 instances under the same conditions (row 5), throughput reached approximately **29.9 mps**.


# Discussion
## Performance Challenges in Large-Scale Deployments
In a situation with millions of sensors publishing frequently to thousands of subscribers, several performance challenges arise end-to-end:
- **Broker Bottlenecks:**
    - **Connection Handling:** Managing TCP connections for millions of publishers and thousands of subscribers consumes significant memory and CPU.
    - **Message Ingestion & Routing:** Processing incoming messages, matching topics to a vast number of subscriptions, and fanning out messages is CPU-intensive.
    - **Memory Management:** Buffering messages (especially for QoS 1/2, or if subscribers are slow) can lead to high memory usage, as observed in our tests at a smaller scale.
    - **Persistence:** If messages need to be persisted (for QoS 1/2 offline clients or retained messages), disk I/O becomes a bottleneck.

- **Network Latency and Bandwidth:**
    - **WAN Latency:** For geographically distributed sensors/subscribers, round-trip times for acknowledgements (QoS 1/2) increase, reducing effective throughput and increasing resource hold times on the broker.
    - **Bandwidth Congestion:** High volumes of messages, especially with larger payloads, can saturate network links, leading to packet loss and retransmissions. This is particularly problematic for constrained IoT device networks.

- **Publisher Limitations:**
    - Constrained devices may lack CPU/memory to handle high publishing rates or complex QoS handshakes reliably.

- **Subscriber Limitations:**
    - Subscribing clients need to be able to process the incoming messages. If a subscriber is slow, messages might queue up at the broker (if QoS > 0 from publisher and broker supports it) or be dropped.
 
## Where Messages Might Be Lost:
- **Publisher Side:** Insufficient buffer space in the MQTT client; network interface queue overflows before TCP ACKs; client crashes.
- **Network (Publisher to Broker):** Congestion leading to packet drops; router buffer overflows; intermittent connectivity.
- **Broker Side:**
    - Input buffers overflowing if ingestion rate exceeds processing capacity.
    - Topic matching/routing taking too long, causing internal queues to build up.
    - Memory exhaustion leading to dropped messages or client disconnections (as seen in tests).
    - If messages are persisted for offline QoS 1/2 clients and storage fills up or is too slow.
    - Exceeding configured limits (e.g., max queued messages per client).
- **Network (Broker to Subscriber):** Similar to publisher-to-broker network issues.
- **Subscriber Side:** MQTT client input buffers overflowing if the application callback (on_message) is too slow; application crashes.

## Role of Different QoS Levels in Addressing Challenges
- **QoS 0:**
    - Pros: Minimizes overhead on publisher, broker, and network, maximizing potential throughput if underlying network is reliable. Good for high-frequency, low-importance data.
    - Cons: Offers no protection against message loss. Cannot deal with network unreliability.
- **QoS 1:**
    - Pros: Ensures messages are delivered at least once from publisher to broker, and broker to subscriber (if subscriber uses QoS 1). This handles transient network losses by enabling retransmissions.
    - Cons: Increases overhead (PUBACKs). Can lead to duplicates, requiring application-level deduplication. Doesn't guarantee order. Can increase load on broker memory if messages need to be queued for retransmission or for offline clients.
- **QoS 2:**
    - Pros: Provides the highest reliability (exactly once delivery from sender to receiver). Prevents duplicates at the MQTT level. Ideal for critical messages.
    - Cons: Highest overhead (4-part handshake). Can significantly reduce throughput compared to QoS 0/1. Places the most load on publisher, broker, and subscriber resources for state management.

In a large-scale system, a mix of QoS levels is often used: QoS 0 for frequent telemetry, QoS 1 or 2 for critical commands or events.

## Why 'Retaining' Messages Can Be Problematic in High-Volume Contexts
MQTT's "retained message" flag allows the broker to store the last known good message on a topic and deliver it to new subscribers immediately upon subscription.

- **Problems in High-Volume, Frequent Update Scenarios:**
    1. **Broker Resource Consumption:** If millions of topics have retained messages, this consumes significant broker memory/storage, especially if messages are large.
    2. **Stale Data:** For topics with very frequent updates (e.g., sensor readings every second), the "last retained message" can become stale almost instantly. A new subscriber might receive an outdated value, which could be misleading.
    3. **Processing Overhead for New Subscribers:** If a client subscribes to a wildcard that matches thousands of topics, each with a retained message, the client (and broker) must process this initial flood of retained messages, which can be overwhelming.
    4. **Churn:** If topics are created and destroyed frequently, managing the lifecycle of retained messages adds complexity.

In high-frequency scenarios, it's often better for new subscribers to wait for fresh, live data rather than receiving a potentially large volume of (potentially stale) retained messages. Retained messages are more suited for slowly changing status information.

# Conclusion
This experimental investigation provided valuable insights into MQTT performance. Key findings include:
- The system achieved high throughput (up to ~7000 mps for a single publisher with 0ms delay and 0 byte payloads) within its resource limits.
- System RAM capacity was a significant limiting factor for tests involving 0ms delay, multiple publishers, and larger message sizes, leading to 100% message loss in such scenarios. This underscores the importance of system provisioning in relation to expected MQTT load.
- For reliable 100ms delay tests, message loss was negligible (0%) with QoS 0, and inter-message arrival gaps were consistent and close to the programmed delay.
- High out-of-order message percentages were observed in some high-load 0ms delay scenarios, even with a single publisher, indicating significant message reordering by the broker or network under stress.
- The $SYS topics provided useful, albeit high-level, correlation with broker load, with increased message traffic on these topics observed for higher application message rates and more demanding Analyzer QoS levels (e.g., QoS 2).
- The choice of MQTT QoS level presents a clear trade-off: higher QoS levels offer greater reliability guarantees but come with increased overhead that can impact maximum throughput and broker/client resource utilization.

This study demonstrated that while MQTT is a lightweight and efficient protocol, its practical application performance is heavily influenced by the chosen operational parameters, the underlying system resources, and the specific capabilities of the MQTT broker implementation. Careful consideration of these factors is essential when designing and deploying large-scale IoT solutions based on MQTT.


















