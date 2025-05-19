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
    -  ![QoS0](./assets/QoS0.png)
    -  **Observation:** This capture illustrates a typical MQTT Quality of Service (QoS) 0 message flow.
          - Packets 4 & 6 show the client (::1) establishing a connection with the broker (::1) via Connect Command and Connect Ack.
          - Packets 8 & 9 show the client subscribing to a topic (test/qos0) and the broker acknowledging the subscription (Subscribe Ack).
          - Packets 18 & 19 demonstrate the core of QoS 0: the client sends two Publish Message packets to the topic test/qos0. Crucially, there are no subsequent MQTT-level acknowledgements from the broker specifically for these individual publish messages. This "fire and forget" mechanism offers the lowest overhead but no delivery guarantee.
          - Packets 22 & 27 show Disconnect Req, and packets 32 & 33 show a Ping Request and Ping Response

- **QoS 1:**
    -  ![QoS1](./assets/QoS1.png)
    -  **Observation:** This capture details an MQTT Quality of Service (QoS) 1 message exchange, guaranteeing "at least once" delivery.
          1. Similar to QoS 0, initial packets involve Connect and Subscribe sequences (packets 19-24 show a connect/subscribe sequence for test/qos1).
          2. Packets 33 & 34 show the client publishing two messages to the topic test/qos1.
          3. For each Publish Message sent by the client (packet 33), the broker responds with a Publish Ack (PUBACK) (packet 36 for message ID=1 from packet 33, and packet 38 for message ID=1 from packet 34). The PUBACK confirms that the broker has received and accepted responsibility for the message. If the publisher does not receive a PUBACK, it will resend the PUBLISH message (with the DUP flag set).
          4. Packet 40 shows a Disconnect Req.
    - This ensures the message is delivered at least once. If acknowledgements are lost, retransmissions (with DUP flag set) can occur, potentially leading to duplicate message delivery at the application layer if not handled by the subscriber.

- **QoS 2:**
    -  ![QoS2](./assets/QoS2.png)
    -  **Observation:** This capture illustrates the four-part handshake of an MQTT Quality of Service (QoS) 2 message exchange, ensuring "exactly once" delivery.
          1. Following connection and subscription (packets 6-9 for test/qos2), the QoS 2 flow for a single message begins.
          2. Packet 18: Client sends Publish Message (ID=1) to the broker.
          3. Packet 19: Broker responds with Publish Received (PUBREC) (ID=1), confirming it has received and stored the message, and is responsible for it.
          4. Packet 21: Client, upon receiving PUBREC, sends Publish Release (PUBREL) (ID=1), instructing the broker to deliver the message and confirming it will not resend this PUBLISH.
          5. Packet 24: Broker, after successfully processing/delivering the message, responds with Publish Complete (PUBCOMP) (ID=1), informing the publisher that the transaction for this message is complete.
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
    - For `Publisher_delay_ms = 0ms`, `Publisher_msg_size_bytes = 0`, and a single publisher instance (row 8), a peak sustained throughput of **6973.3 mps** was recorded by the analyzer. This demonstrates the high potential message rate for a single, unconstrained publisher sending small messages.
      ![Mean Throughput vs. Publisher Instances by Publisher QoS](./assets/throughput-analysis01.png)
 
- **Effect of Number of Publisher Instances (at 0ms delay):**
    - When message size was 0 bytes and publisher QoS was 0:
      - 1 Instance (row 8): ~6973 mps
      - 5 Instances (row 9): ~9746 mps (aggregate). While higher than 1 instance, it's not a 5x scaling, suggesting system contention or broker limits are being approached.
      - 10 Instances (row 10): ~8658 mps (aggregate). Throughput decreased compared to 5 instances, strongly indicating that the system (broker or test machine) was overloaded.

- **Effect of Message Size (at 0ms delay, 1 Publisher Instance, PuBQoS 0):**
    - 0 bytes (row 8): ~6973 mps
    - 1000 bytes (row 11): ~5445 mps
    - As message size increased, throughput decreased, which is expected due to the higher overhead of processing and transmitting larger messages. Tests with 4000 byte messages at 0ms delay (rows 14-16) resulted in 0 messages received due to system limitations.
      ![Mean Throughput vs. Message Size by Publisher QoS and Delay](./assets/throughput-analysis02.png)

- **Effect of QoS Levels on Throughput (100ms delay):**
    - Comparing rows 4 (Analyzer QoS 0, Pub QoS 0, ~9.97mps) and the "AnalyzerQoSChangeTest" rows 6 (AQoS0, PQoS0, ~9.97 mps) and row 7 (AQoS2, PQoS0, ~9.97 mps), the analyzer's subscription QoS had a negligible impact on the application message throughput received from a QoS 0 publisher in this stable 100ms delay scenario.
 
## Message Loss
Message loss was calculated based on the highest message counter received from each publisher versus the number of unique messages received from it.

- **Delay=100ms Tests:**
    - For the reliable tests shown (rows 4, 5, 6, 7), message loss was consistently 0.0%. This indicates excellent reliability when the message rate was constrained.
    - However, a large number of subsequent 100ms delay tests (rows 17-25) showed 100% loss. This is unexpected for 100ms delay and suggests that the system had entered a persistent failure state after the initial high-load 0ms delay tests, likely due to RAM exhaustion not fully recovering or processes not restarting/reconnecting correctly.
- **Delay=0ms Tests:**
    - 1 Instance, 0 byte messages (row 8): **0.217% loss**.
    - 5 Instances, 0 byte messages (row 9): **66.165% loss**. Loss increased dramatically.
    - 10 Instances, 0 byte messages (row 10): **65.206% loss**. Similar high loss.
    - 1 Instance, 1000 byte messages (row 11): **56.35% loss**.
    - These indicate that even before total system RAM exhaustion (which led to 100% loss in rows 12-16), the 0ms delay tests were already experiencing significant message loss, likely due to broker or client-side Paho MQTT buffers overflowing or network stack drops under extreme load.
![Avg Message Loss vs Publisher QoS](./assets/loss01.png)
![Avg Message Loss by Analyzer QoS, PubQoS and delay](./assets/loss02.png)

## Out-of-Order Messages
- **Delay=100ms Tests:** In the reliable tests (rows 4, 5, 6, 7), out-of-order messages were 0.0%.
- **Delay=0ms Tests:**
    - 1 Instance, 0 byte messages (row 8): **0.001%**
    - 5 Instances, 0 byte messages (row 9): **0.003%**
    - 10 Instances, 0 byte messages (row 10): **29.693%**. This is a very high percentage, indicating significant message reordering when 10 publishers sent small messages at maximum speed (QoS 0).
    - 1 Instance, 1000 byte messages (row 11): **0.0%**
    - Row 64 (AQoS2, PQoS0, Delay=0, MsgSize=1000, Inst=1): **71.994%**. This exceptionally high OOO rate for a single publisher (even though sending PuBQoS 0) suggests severe processing delays or reordering within the broker or network path under the load of large messages at high speed, despite the analyzer attempting a QoS 2 subscription.
- **General Trend:** Out-of-order messages were primarily observed in high-load, 0ms delay scenarios, particularly with a higher number of publishers.
![out of order percentage (loss < 100% tests)](./assets/ooo.png)

## Duplicate Messages
- Across the provided data snippet, duplicate messages were extremely rare. Only row 70 (AQoS=1, PQoS=0, Delay=0, MsgSize=1000, Inst=5) showed a minor 0.079%.
- Duplicates are an expected behavior primarily with Publisher QoS 1 if acknowledgements (PUBACKs) are lost, prompting re-transmissions. The observed duplicate with Publisher QoS 0 is anomalous and could be due to a rare network-level event or a broker-side hiccup under the specific high load of that test.

## Inter-Message Gap
- **Delay=100ms tests:**
    - Rows 4, 6, 7 (1 Instance): Average gap was consistently ~100.35ms with a very low standard deviation (~0.6ms). This accurately reflects the publisher's configured inter-send delay with minimal jitter.
    - Row 5 (3 Instances): Average gap remained ~100.348ms with a slightly higher but still low std dev (~0.777ms), indicating consistent delivery timing even with more publishers at this constrained rate.
- **Delay=0ms tests:**
    - Row 8 (1 Inst, Size 0): Average gap ~0.05ms (StdDev ~0.248ms). Extremely rapid message arrival.
    - Row 10 (10 Inst, Size 0): Average gap increased to ~1.197ms with a very large StdDev of ~18.33ms. This high variability and larger average gap (compared to 1 instance) correlates with the high out-of-order percentage and overall system stress.
    - Row 11 (1 Inst, Size 1000): Average gap ~0.054ms (StdDev ~0.236ms).
    - Row 64 (AQoS2, PQoS0, Delay=0, MsgSize=1000, Inst=1): Average gap ~0.053ms (StdDev ~0.249ms), despite extremely high OOO. This indicates that when messages did arrive consecutively, they did so quickly.

## Correlation with $SYS Topics 
- **Broker Message Load:**
    - A positive correlation was observed between the application-level Mean_total_rate_mps_analyzer and the broker's reported messages sent/received per minute. For example, in row 4 (1 instance, 100ms delay, ~10mps), SYS_load_messages_sent_1min_last was ~544. In row 5 (3 instances, 100ms delay, ~30mps), it increased to ~1187.
    - During high-throughput 0ms delay tests (e.g., row 8, ~6973 mps), SYS_load_messages_sent_1min_last was exceptionally high at ~273,483.
    - The "AnalyserQoSChangeTest" (rows 6 and 7) showed that when the Analyser subscribed with QoS 2 (row 7, SYS_load_messages_sent_1min_last ~712) versus QoS 0 (row 6, SYS_load_messages_sent_1min_last ~454), the broker reported a higher number of messages sent, reflecting the additional MQTT control packets (PUBREC, PUBREL, PUBCOMP) required to service the QoS 2 subscription, even though the application message rate was the same.
![Throughput vs. Broker Messages sent (SYS)](./assets/SYS.png)
![Correlation Matrix of Selected Metrics](./assets/corr_matrix.png)

- **Active Clients and Subscriptions:**
    - These metrics generally increased as more publisher instances were configured to be active, as expected. For instance, SYS_clients_active_last was 3 for 1 publisher (row 4) and increased to 5 for 3 publishers (row 5). For tests with 10 active publishers, it reached 12 (row 8). Similar trends were seen for subscription counts.
- **Messages Stored:**
    - This was 'N/A' for most tests in the snippet where $SYS data was available, then showed values like 53, 55, 56, 64 for some high-load 0ms delay tests (rows 62, 63, 64, 70). An increase here suggests the broker is queuing messages, potentially due to inability to deliver them as fast as they are received, which can be an indicator of overload.
- **Missing $SYS Data:** For a large portion of the tests that failed due to RAM capping (rows 12 onwards, and then most tests from row 17), the $SYS topic data was reported as 'N/A'. This strongly indicates that either the broker was too overwhelmed to publish its $SYS updates, or the analyser itself was unable to subscribe to or process these $SYS messages during those periods of system instability.

## System Limitations
As previously stated, the most significant factor impacting the test results for high-load scenarios (Publisher_delay_ms = 0, high instance counts, large message sizes) was the exhaustion of system RAM. 
Tests consistently failed (0 messages received, 100% loss, 'N/A' for many $SYS topics) when these demanding parameters were combined. For example, with 0ms delay, Publisher QoS 0:
- 5 Instances, 1000 byte messages (row 12)
- 10 Instances, 1000 byte messages (row 13)
- 1, 5, or 10 Instances, 4000 byte messages (rows 14, 15, 16)
This demonstrates a clear boundary condition of the test environment. While MQTT itself might handle higher rates, the supporting system (Paho clients, Python runtime, Mosquitto broker on the given hardware, OS networking stack) could not sustain the memory pressure generated by the extremely rapid creation and buffering of messages by multiple publishers.
The successful 0ms delay tests (e.g., 1 publisher, 0-byte messages achieving ~7000 mps) show the potential before this RAM limit is breached.

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


# Bibliography
[1] MQTT Version 3.1.1. Available at: https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html (Accessed: 11 May 2025). 
[2] 















