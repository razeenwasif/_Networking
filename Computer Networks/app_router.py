import socket 
import netifaces
import hashlib
import time 
import sys 
import random # for basic route cost simulation 

# ---- Configuration ---- 
LISTEN_PORT = 3310 
BUFFER_SIZE = 2048 # Max UDP payload size 
PACKET_DELIMITER = '*'
PAIR_SEPARATOR = ':'
DEFAULT_DELAY_SECONDS = 3 
ROUTER_COST = random.randint(1, 5) # simulate a cost for traversing this router 

# ---- Helper Functions ---- 
def get_network_info():
    """
    Finds a suitable non-loopback IPv4 interface and returns its 
    IP address, netmask, and broadcast address.
    Returns None if no suitable interface is found.
    """
    try:
        # List all interfaces
        interfaces = netifaces.interfaces()
        for iface_name in interfaces:
            iface_details = netifaces.ifaddresses(iface_name)
            # Look for Ipv4 vonfiguration 
            if netifaces.AF_INET in iface_details:
                ipv4_info = iface_details[netifaces.AF_INET][0]
                ip_addr = ipv4_info.get('addr')
                netmask = ipv4_info.get('netmask')
                # ignore loopback addresses 
                if ip_addr and not ip_addr.startswith('127.'):
                    # Broadcast might not always be present, calculate if needed 
                    broadcast = ipv4_info.get('broadcast')
                    if not broadcast and ip_addr and netmask:
                        # very basic broadcast calculation (may not be universally perfect)
                        ip_parts = list(map(int, ip_addr.split('.')))
                        mask_parts = list(map(int, netmask.split('.')))
                        bcast_parts = [(ip_parts[i] | (~mask_parts[i] & 255)) for i in range(4)] 
                        broadcast = '.'.join(map(str, bcast_parts))

                    if ip_addr and netmask and broadcast:
                        print(f"[*] Using interface {iface_name}:")
                        print(f"    IP Address: {ip_addr}")
                        print(f"    Netmask:    {netmask}")
                        print(f"    Broadcast:  {broadcast}")
                        return ip_addr, netmask, broadcast 

    except ImportError:
        print("[!] ERROR: 'netifaces' library not found.")
        sys.exit(1)
    except Exception as e:
        print(f"[!] ERROR: Could not get network interface details: {e}")
        print("[!] INFO: Falling back to 0.0.0.0 binding, broadcast may fail.")
        # Fallback, but broadcast/destination check might be unreliable
        return '0.0.0.0', '255.255.255.0', '255.255.255.255'

    print("[!] ERROR: No suitable non-loopback IPv4 interface found.")
    # Fallback, but broadcast/destination check might be unreliable
    return '0.0.0.0', '255.255.255.0', '255.255.255.255'
    # Or exit: sys.exit("Error: No suitable network interface found.")

def parse_payload(payload_str):
    """
    Parses the Key:Value*Key:Value string into a dictionary.
    """
    payload_dict = {}
    try:
        parts = payload_str.split(PACKET_DELIMITER)
        for part in parts:
            if PAIR_SEPARATOR in part:
                key,value = part.split(PAIR_SEPARATOR, 1)
                payload_dict[key.strip()] = value.strip()
            # Handle potential empty parts from trailing/double delimiters
            elif part.strip():
                print(f"[!] Warning: Malformed part in payload: '{part}'")
                # Decide how to handle - ignore or raise error? For robustness, maybe ignore.
    except Exception as e:
        print(f"[!] ERROR: Failed to parse payload: {e}")
        return None # Indicate parsing failure 
    return payload_dict

def format_payload(payload_dict, fields_order):
    """
    Formats a dictionary back into the Key:Value*Key:Value string,
    maintaing a specific order for consistent checksum calculation.
    Excludes the 'Checksum' field itself from the ordered list for checksumming.
    """
    parts = []
    for key in fields_order:
        if key != 'Checksun' and key in payload_dict:
            # Special handling for Hop field if it's a list (though spec implies adding sequentially)
            # for now, assume hop fields are just added to the dict like others
            parts.append(f"{key}{PAIR_SEPARATOR}{payload_dict[key]}")

    # Ad any Hop fields specifically (as they are appended)
    hop_keys = sorted([k for k in payload_dict if k.startswith('Hop')])
    for key in hop_keys:
        parts.append(f"{key}{PAIR_SEPARATOR}{payload_dict[key]}")

    # Checksum is calculated *before* adding the Checksum field itself 
    payload_for_checksum = PACKET_DELIMITER.join(parts)

    # Now add the actual checksum field for the final payload
    if 'Checksum' in payload_dict:
        parts.append(f"Checksum{PAIR_SEPARATOR}{payload_dict['Checksum']}")

    return PACKET_DELIMITER.join(parts), payload_for_checksum 


def calculate_checksum(data_str):
    """
    Calculates the MD5 checksum (hex digest) of the input string
    """
    return hashlib.md5(data_str.encode('utf-8')).hexdigest()

def create_error_packet(original_sender_ip, error_message, local_ip):
    """Creates an Error (ER) packet string"""
    error_payload = {
        "Src" : local_ip,
        "Dest" : original_sender_ip,
        "PT" : "ER",
        "MS" : error_message,
        "HC" : "1", # hop count starts at 1 
        "RC" : "0", # no route cost for error typically 
    }
    # Define order for error packets (simpler)
    fields_order = ["Src", "Dest", "PT", "MS", "HC", "RC"]
    payload_str_for_checksum, _ = format_payload(error_payload, fields_order) # we need the partial string 
    checksum = calculate_checksum(payload_str_for_checksum)
    error_payload["Checksum"] = checksum 
    final_payload_str, _ = format_payload(error_payload, fields_order + ["Checksum"]) # format with checksum 

    return final_payload_str.encode('utf-8')


# ---- Main Router Logic ---- 
if __name__ == "__main__":
    MY_IP, MY_NETMASK, MY_BROADCAST = get_network_info()
    if not MY_IP:
        sys.exit(1) # exit if we couldn't get network info 

    # Create and bind the UDP socket 
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
    # Bind to specific IP is possible, otherwise 0.0.0.0 (all interfaces)
        bind_ip = MY_IP if MY_IP != '0.0.0.0' else '0.0.0.0'
        sock.bind((bind_ip, LISTEN_PORT))
        # Allow broadcasting from this socket 
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        print(f"[*] Router listening on {bind_ip}:{LISTEN_PORT}")
        print(f"[*] This router's simulated cost: {ROUTER_COST}")
        print(f"[*] Configured delay between processing: {DEFAULT_DELAY_SECONDS}s")

    except OSError as e:
        print(f"[!] ERROR: Binding socket failed: {e}")
        print(f"[!] INFO: Port {LISTEN_PORT} might already be in use.")
        sys.exit(1)

    # Main listening loopback
    try:
        while True: 
            print("\n[*] Waiting for packet...")
            try:
                # Receive packet
                data, sender_address = sock.recvfrom(BUFFER_SIZE)
                payload_str = data.decode('utf-8')
                sender_ip = sender_address[0]
                print(f"[*] Received packet from {sender_ip}: \n   '{payload_str}'")

                # 1. Parse the payload 
                payload_dict = parse_payload(payload_str)
                if payload_dict is None:
                    print("[!] ERROR: Packet parsing failed. Sending ER packet.")
                    error_pkt = create_error_packet(sender_ip, "Packet format error", MY_IP)
                    sock.sendto(error_pkt, sender_address)
                    continue # wait for next packet 

                # Define the expected field order for consistent checksumming
                # This order matters! Based on the example.
                # Note: Checksum and Hops are handled specially.
                initial_fields_order = ["Src", "Dest", "PT", "MS", "HC", "RC"] # Adjust MS if not always present


                # 2. Validate Checksum
                received_checksum = payload_dict.get('Checksum')
                # Format payload *without* checksum field to recalculate
                _, payload_for_checksum_calc = format_payload(payload_dict, initial_fields_order)

                calculated_checksum = calculate_checksum(payload_for_checksum_calc)

                if not received_checksum or received_checksum.lower() != calculated_checksum.lower():
                    print(f"[!] ERROR: Checksum mismatch! Rec: {received_checksum}, Calc: {calculated_checksum}")
                    print(f"[!]        Data used for calc: '{payload_for_checksum_calc}'")
                    error_pkt = create_error_packet(sender_ip, "Checksum validation failed", MY_IP)
                    sock.sendto(error_pkt, sender_address)
                    continue # Wait for next packet
                else:
                    print("[*] Checksum VALID.")


                # 3. Process/Forward Logic
                dest_ip = payload_dict.get('Dest')

                # Add artificial delay
                print(f"[*] Sleeping for {DEFAULT_DELAY_SECONDS} second(s)...")
                time.sleep(DEFAULT_DELAY_SECONDS)

                # --- Decision Making ---
                if dest_ip == MY_IP or dest_ip == MY_BROADCAST:
                    # Packet is for this router or broadcast
                    print(f"[*] Packet destination ({dest_ip}) is me or broadcast.")
                    print(f"[*]  -> Packet Type: {payload_dict.get('PT', 'N/A')}")
                    print(f"[*]  -> Message:     {payload_dict.get('MS', 'N/A')}")
                    print(f"[*]  -> Route Info:  HC={payload_dict.get('HC')}, RC={payload_dict.get('RC')}")
                    # In a real scenario, you might handle different PTs (LS, DV) here.
                    # For now, just acknowledge receipt by printing.
                    # You might optionally send a reply back to the source here.

                elif dest_ip:
                    # Packet needs forwarding
                    print(f"[*] Packet destination ({dest_ip}) is not me. Preparing to forward...")

                    # Modify packet: Increment HC, RC, add Hop
                    try:
                        hc = int(payload_dict.get('HC', 0)) + 1
                        rc = int(payload_dict.get('RC', 0)) + ROUTER_COST # Add this router's cost
                    except ValueError:
                         print("[!] ERROR: Invalid HC or RC value in packet. Cannot forward reliably.")
                         error_pkt = create_error_packet(sender_ip, "Invalid HC/RC format", MY_IP)
                         sock.sendto(error_pkt, sender_address)
                         continue

                    payload_dict['HC'] = str(hc)
                    payload_dict['RC'] = str(rc)

                    # Find highest existing Hop number to append correctly
                    hop_num = 0
                    for k in payload_dict.keys():
                        if k.startswith('Hop'):
                             try:
                                 # Extract number if format is HopN:IP (adjust if just Hop:IP)
                                 # Assuming just Hop:IP as per spec example g.
                                 hop_num += 1
                             except:
                                pass # Ignore if key isn't numbered as expected

                    # Add *this* router's IP to the hop list (using simple Hop:IP)
                    # The key 'Hop' might appear multiple times. Need a way to distinguish.
                    # Simplest based on spec: append another 'Hop' field.
                    # Let's find the max hop number used if keys were Hop1, Hop2 etc.
                    # But spec shows multiple Hop:IP... let's stick to that.
                    # How to handle multiple keys with same name in dict? Last one wins.
                    # Workaround: Use unique keys or handle hops separately.
                    # Let's treat Hops as needing special formatting based on *order*
                    # Re-thinking: The format_payload should handle adding the hops.
                    # Add the current hop to the dictionary to be included by format_payload
                    # Need a unique key for the dict, use hop count?
                    # Or just append directly when formatting? Spec says "Add ... to the end"
                    # Let's try adding to dict with a counter (not ideal)
                    #payload_dict[f"Hop{hop_num+1}"] = MY_IP # NO - spec is Hop:IP multiple times

                    # Ok, let's store hops separately and format carefully
                    hops = [f"Hop{PAIR_SEPARATOR}{v}" for k, v in payload_dict.items() if k.startswith("Hop")]
                    hops.append(f"Hop{PAIR_SEPARATOR}{MY_IP}")

                    # Create payload string for *new* checksum calculation
                    # Need all fields *except* old checksum, plus the *new* HC/RC/Hop
                    temp_payload_dict = payload_dict.copy()
                    temp_payload_dict.pop('Checksum', None) # Remove old checksum if present
                    # Remove old hops to avoid duplication by format_payload's default loop
                    for k in list(temp_payload_dict.keys()):
                        if k.startswith("Hop"):
                            del temp_payload_dict[k]

                    parts_for_checksum = []
                    for key in initial_fields_order:
                        if key in temp_payload_dict:
                             parts_for_checksum.append(f"{key}{PAIR_SEPARATOR}{temp_payload_dict[key]}")
                    # Append the *updated* hop list strings
                    parts_for_checksum.extend(hops)
                    payload_str_for_new_checksum = PACKET_DELIMITER.join(parts_for_checksum)


                    # Calculate new checksum
                    new_checksum = calculate_checksum(payload_str_for_new_checksum)

                    # Construct final payload string including the new checksum and hops
                    final_parts = parts_for_checksum + [f"Checksum{PAIR_SEPARATOR}{new_checksum}"]
                    final_payload_str = PACKET_DELIMITER.join(final_parts)
                    final_payload_bytes = final_payload_str.encode('utf-8')


                    # **Determine Next Hop**
                    # THIS IS THE TRICKY PART - "How do you find one that is running? Ask the room!"
                    # For now, we'll just flood the subnet using the broadcast address.
                    # In a real routing protocol (like DV or LS), you'd consult a routing table.
                    next_hop_address = (MY_BROADCAST, LISTEN_PORT)
                    print(f"[*] Flooding modified packet to subnet broadcast {MY_BROADCAST}:{LISTEN_PORT}")
                    print(f"[*] Forwarding payload: \n    '{final_payload_str}'")
                    sock.sendto(final_payload_bytes, next_hop_address)

                else:
                     print("[!] ERROR: Packet has no destination IP ('Dest' field missing).")
                     # Optionally send error back

            except UnicodeDecodeError:
                print(f"[!] ERROR: Received non-UTF8 data from {sender_address}. Ignoring.")
            except Exception as e:
                print(f"[!] UNEXPECTED ERROR during packet processing: {e}")
                # Attempt to send generic error back?
                try:
                     error_pkt = create_error_packet(sender_ip, f"Internal router error: {e}", MY_IP)
                     sock.sendto(error_pkt, sender_address)
                except Exception as send_err:
                     print(f"[!] Additionally failed to send error packet: {send_err}")


    except KeyboardInterrupt:
        print("\n[*] Router shutting down.")
    finally:
        sock.close()
        print("[*] Socket closed.")



# Example using netcat (nc):
"""
Let's craft a sample packet to send to this router (172.18.0.1). 
We'll pretend the packet originates from 172.18.0.10 and is ultimately 
destined for 172.18.0.20.

1. Prepare the payload (without checksum):
```bash
Src:172.18.0.10*Dest:172.18.0.20*PT:MS*MS:Test message 1*HC:1*RC:0
```

2. Calculate the MD5 Checksum for the string above. You can use an 
online tool or a command-line utility:
```bash
echo -n "Src:172.18.0.10*Dest:172.18.0.20*PT:MS*MS:Test message 1*HC:1*RC:0" | md5sum
```
Let's assume the output starts with e8a4.... (Use the actual checksum you get).

3. Construct the full packet String:
```bash
Src:172.18.0.10*Dest:172.18.0.20*PT:MS*MS:Test message 
    1*HC:1*RC:0*Checksum:e8a4...your_full_checksum_here...
```

4. Send using netcat:
Open a new terminal window (don't stop the router script).
Run this command, replacing the checksum with the one you calculated:
```
echo -n "Src:172.18.0.10*Dest:172.18.0.20*PT:MS*MS:Test message 
    1*HC:1*RC:0*Checksum:e8a4...your_full_checksum_here..." | nc -u 172.18.0.1 3310
```

    echo -n: Prints the string without a trailing newline.

    |: Pipes the output to netcat.

    nc -u: Runs netcat in UDP mode.

    172.18.0.1: The IP address of your running router script.

    3310: The port your router script is listening on.
"""
