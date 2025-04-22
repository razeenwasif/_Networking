import socket
import sys
import time
import datetime
import traceback
from collections import deque

# --- Configuration ---
DEFAULT_GOPHER_PORT = 70
SOCKET_TIMEOUT = 10  # seconds
BUFFER_SIZE = 65536   # Bytes to read at a time
MAX_FILE_DOWNLOAD_SIZE = 10 * 1024 * 1024 # 10MiB

# --- Gopher Item Types ---
TEXT = '0'
DIRECTORY = '1'
CSO = '2'
ERROR = '3'
MAC_BINHEX = '4'
DOS_ARCHIVE = '5'
UUENCODED = '6'
SEARCH = '7'
TELNET = '8'
BINARY = '9'
REDUNDANT = '+' 
TN3270 = 'T'
GIF = 'g'
IMAGE = 'I'
HTML = 'h'
INFO = 'i'

# Sets for type checking
BINARY_TYPES = {
    BINARY, MAC_BINHEX, DOS_ARCHIVE,
    UUENCODED, GIF, IMAGE
}
# Types that are acknowledged but not processed
IGNORED_INTERACTIVE_TYPES = {
    SEARCH, TELNET, TN3270,
    HTML, CSO
}

# --- Helper Functions ---

def log_request(selector):
    """Prints a timestamped log message for a request being sent."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    printable_selector = selector.replace('\r', '\\r').replace('\n', '\\n') if selector else "(root selector)"
    print(f"{timestamp} - Requesting selector: '{printable_selector}'")

def parse_gopher_line(line):
    """Parses a single line from a Gopher directory listing."""
    if not line or len(line) < 1: return None # input line empty
    item_type = line[0] # first char of any Gopher line is the item type (RFC 1436)
    parts = line[1:].split('\t') # split remaining parts on TAB (RFC 1436)
    
    # parts -> Display, Selector, Host, Port 
    if len(parts) < 4:
        # Gopher "info" messages are an exception to the 4-part rule
        if item_type == INFO and len(parts) >= 1:
             return {'type': item_type, 'display': parts[0].strip(), 'selector': '', 'host': '', 'port': 0}
        # malformed if line had fewer than 4 parts and it wasn't a valid 'info' message 
        print(f"Warning: Malformed line (short): {line.strip()}", file=sys.stderr)
        return None

    try:
        port = int(parts[3].strip())
    except ValueError:
        print(f"Warning: Invalid port in line: {line.strip()}", file=sys.stderr)
        return None
    
    # construct dict containing all the extracted and cleaned pieces of info 
    # 0: Display string; 1: Selector; 2; Host; 3: Port 
    return {'type': item_type, 'display': parts[0].strip(), 'selector': parts[1].strip(),
            'host': parts[2].strip(), 'port': port}

def connect_and_request(host, port, selector):
    """
    This function establishes a network connection (TCP) to a specified 
    Gopher server (host and port). Sends a Gopher request (the selector) 
    to that server over the established connection. Receive the complete 
    response sent back by the server. Handle potential network errors.
    Return the raw response data as bytes, or indicate failure.

    Inputs:
        * string host: The hostname or IP address of the Gopher 
                       server to connect to.
        * int port: The port number the Gopher server is listening on.
        * string selector: The specific resource being requested from the 
                           server.
    Output:
        * bytes object: If successful, object contains the raw, complete 
                        data sent back.
        * None: if any error occurs, return nothing.
    """
    log_request(selector)
    # init buffer. bytearray good for building up response piece by piece 
    response_data = bytearray()
    request_str = selector + '\r\n' # rfc 1436 CRLF terminator
    download_limit_exceeded = False # check for abnormal termination 
    try:
        # Encode request 
        try:
            request_bytes = request_str.encode('utf-8')
        except UnicodeEncodeError:
            # fallback charset specified in rfc 1436
            request_bytes = request_str.encode('latin-1', errors='replace')

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(SOCKET_TIMEOUT)
            # Resolve hostname just before connect
            ip_address = socket.gethostbyname(host)
            s.connect((ip_address, port))
            s.sendall(request_bytes)

            # Receive response until server finished sending 
            while True:
                try:
                    chunk = s.recv(BUFFER_SIZE)
                    if not chunk: break # Connection closed
                    response_data.extend(chunk)

                    # check download size limit 
                    if len(response_data) > MAX_FILE_DOWNLOAD_SIZE:
                        print(f"Error: Download limit ({MAX_FILE_DOWNLOAD_SIZE / (1024*1024):.1f} MiB)" f"exceeded for selector '{selector}'. Aborting download.", file=sys.stderr)
                        download_limit_exceeded = True 
                        break 
                except socket.timeout:
                    print(f"Error: Socket timeout receiving from {host}:{port} for '{selector}'", file=sys.stderr)
                    return None
                except socket.error as e:
                    print(f"Error: Socket error receiving from {host}:{port} for '{selector}': {e}", file=sys.stderr)
                    return None

            # if loop was exited due to size limit, return none 
            if download_limit_exceeded: return None

            # Check for Gopher directory termination sequence (bytes comparison)
            term1 = b'\r\n.\r\n'
            term2 = b'\n.\n'   
            term3 = b'.\r\n'   
            if response_data.endswith(term1):
                return bytes(response_data[:-len(term1)])
            elif response_data.endswith(term2):
                 return bytes(response_data[:-len(term2)])
            elif response_data.endswith(term3):
                 return bytes(response_data[:-len(term3)])
            else:
                 return bytes(response_data) # terminated by close

    except socket.timeout:
        print(f"Error: Connection timed out to {host}:{port}", file=sys.stderr)
        return None
    except socket.gaierror as e:
         print(f"Error: Could not resolve/connect to host '{host}': {e}", file=sys.stderr)
         return None
    except socket.error as e:
        print(f"Error: Socket error connecting/sending to {host}:{port}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: Unexpected error during request to {host}:{port} for '{selector}': {e}", file=sys.stderr)
        return None

# --- Main Crawler Class ---

class GopherCrawler:
    def __init__(self, start_host, start_port):
        self.start_host = start_host
        self.start_port = start_port
        self.directories_to_visit = deque(['']) # Start with root selector ""
        self.visited_selectors = set(['']) # Keep track of visited selectors ON THIS SERVER
        self.external_servers = {} # Dict: (host, port) -> status ("up", "down/error")

        # Statistics - Initialize directly
        self.stats = {
            'dir_count': 1, # Start with root
            'text_files': [], 'binary_files': [],
            'invalid_references': [], 'request_errors': [],
            'smallest_text': {'size': float('inf'), 'selector': None, 'content': None},
            'largest_text': {'size': 0, 'selector': None},
            'smallest_binary': {'size': float('inf'), 'selector': None},
            'largest_binary': {'size': 0, 'selector': None}
        }

    def check_external_server(self, host, port):
        """Checks if an external Gopher server is reachable. Caches results."""
        server_key = (host, port)
        # check if server already found 
        if server_key in self.external_servers:
            return self.external_servers[server_key]

        print(f"--- Checking external server: {host}:{port} ---")
        response_bytes = connect_and_request(host, port, '') # Simple root request
        status = "up" if response_bytes is not None else "down/error"
        print(f"--- External server {host}:{port} is {status.upper()} ---")
        self.external_servers[server_key] = status
        return status

    def _decode(self, data_bytes):
        """Try UTF-8, fallback to Latin-1 for decoding."""
        try:
            return data_bytes.decode('utf-8')
        except UnicodeDecodeError:
            print(f"Warning: Decoding failed for UTF-8, using latin-1.", file=sys.stderr)
            return data_bytes.decode('latin-1', errors='replace')

    def _process_file(self, item, is_binary):
        """Helper to download a file and update stats."""
        selector = item['selector']
        file_content_bytes = connect_and_request(self.start_host, self.start_port, selector)

        if file_content_bytes is not None:
            size = len(file_content_bytes)
            file_list = self.stats['binary_files'] if is_binary else self.stats['text_files']
            file_list.append((selector, size))

            key_prefix = "binary" if is_binary else "text"
            smallest_key = 'smallest_' + key_prefix
            largest_key = 'largest_' + key_prefix

            # Update smallest
            if size < self.stats[smallest_key]['size']:
                self.stats[smallest_key]['size'] = size
                self.stats[smallest_key]['selector'] = selector
                # Store content ONLY for the smallest *text* file
                if not is_binary:
                    self.stats[smallest_key]['content'] = self._decode(file_content_bytes)

            # Update largest
            if size > self.stats[largest_key]['size']:
                self.stats[largest_key]['size'] = size
                self.stats[largest_key]['selector'] = selector
        else:
            # Request failed 
            self.stats['request_errors'].append(selector + " (fetch failed)")


    def process_item(self, item):
        """Processes a single item from a directory listing."""
        item_type = item['type']
        selector = item['selector']

        # Check if it's an external link
        if item['host'] != self.start_host or item['port'] != self.start_port:
            print(f"  -> Found external link: Type={item_type}, Host={item['host']}, Port={item['port']}")
            self.check_external_server(item['host'], item['port'])
            return # Don't add external links to crawl queue 

        # --- Handle items on the *target* server ---
        if selector in self.visited_selectors: return 
        self.visited_selectors.add(selector)

        # Handle based on type
        if item_type == DIRECTORY:
            print(f"  -> Found directory: '{item['display']}', Selector='{selector}'")
            self.directories_to_visit.append(selector)
            self.stats['dir_count'] += 1

        elif item_type == TEXT:
            print(f"  -> Found text file: '{item['display']}', Selector='{selector}'")
            self._process_file(item, is_binary=False)

        elif item_type in BINARY_TYPES:
            print(f"  -> Found binary file: '{item['display']}', Selector='{selector}', Type='{item_type}'")
            self._process_file(item, is_binary=True)

        elif item_type == ERROR:
            print(f"  -> Found error/invalid reference: '{item['display']}', Selector='{selector}'")
            self.stats['invalid_references'].append(selector)

        elif item_type == INFO:
             print(f"  -> Found info message: '{item['display']}'")
             if not selector: self.visited_selectors.remove(selector)

        elif item_type in IGNORED_INTERACTIVE_TYPES:
             print(f"  -> Found ignored type '{item_type}': '{item['display']}', Selector='{selector}'. Acknowledged.")

        else: # Unknown or unhandled type
            print(f"  -> Found unknown/unhandled type '{item_type}': '{item['display']}', Selector='{selector}'. Ignoring.")

    def crawl(self):
        """
        Starts the crawling process.
        Breadth-First Search is used imagining the gopher server as a tree of directories 
        and files such that server can be explored level by level.
        1. Starts at root level (level 0)
        2. finds all directories directly linked from the root 
        3. visits all directories at level 1, finding all directories they link to on level 2 
        4. continues this process, visiting all directories at the current lvl before moving on 
        Done using the self.directories_to_visit queue.
        New directories found are added to the end of the queue. 
        The next directory to visit is always taken from the front of the queue 
        """
        print(f"--- Starting Gopher crawl of {self.start_host}:{self.start_port} ---")

        while self.directories_to_visit:
            current_selector = self.directories_to_visit.popleft()
            print(f"\n--- Crawling directory selector: '{current_selector or '(root)'}' ---")
            # fetch content 
            response_bytes = connect_and_request(self.start_host, self.start_port, current_selector)
            # no content 
            if response_bytes is None:
                print(f"Error: Failed to retrieve directory listing for selector '{current_selector}'. Skipping.", file=sys.stderr)
                self.stats['request_errors'].append(current_selector + " (directory fetch failed)")
                continue
            # else decode fetched content
            response_text = self._decode(response_bytes)

            # Process directory listing line by line
            for line in response_text.splitlines():
                line = line.strip()
                if not line or line == '.': continue # Skip empty/terminator lines
                
                # dict containing extracted fields (type, display, selector, host, port)
                parsed_item = parse_gopher_line(line)
                if parsed_item:
                    try:
                        self.process_item(parsed_item)
                    except Exception as e:
                        item_id = parsed_item.get('selector', f"line:'{line[:30]}...'")
                        print(f"Error: Unexpected error processing item '{item_id}': {e}", file=sys.stderr)
                        self.stats['request_errors'].append(f"{current_selector} -> {item_id} (processing_error)")
                else:
                    # parse_gopher_line returned None (malformed line)
                    print(f"Warning: Skipping malformed line in '{current_selector}': {line}", file=sys.stderr)
                    self.stats['request_errors'].append(f"{current_selector} (malformed_line: {line[:50]}...)")

        print("\n--- Crawl finished ---")

    def _print_file_stats(self, file_type):
        """Helper to print file list and stats."""
        is_binary = (file_type == 'binary')
        files = self.stats[f'{file_type}_files']
        smallest = self.stats[f'smallest_{file_type}']
        largest = self.stats[f'largest_{file_type}']
        type_name_cap = file_type.capitalize()

        print(f"\n{type_name_cap} files found: {len(files)}")
        if files:
            print(f" List of {file_type} files (selector, size):")
            for selector, size in sorted(files):
                print(f" - '{selector}' ({size} bytes)")

            print(f"\nSmallest {file_type} file:")
            if smallest['selector'] is not None:
                print(f" Selector: '{smallest['selector']}'")
                print(f" Size: {smallest['size']} bytes")
                if not is_binary and smallest['content'] is not None:
                     print(f" Content:\n------ START CONTENT ------\n{smallest['content']}\n------ END CONTENT ------")
            else:
                print(" No {file_type} files found")

            print(f"\nLargest {file_type} file:")
            if largest['selector'] is not None:
                 print(f" Selector: '{largest['selector']}'")
                 print(f" Size: {largest['size']} bytes")
            else:
                print(f" No {file_type} files found")
        else:
             print(f" No {file_type} files found")
             print(f"\nSmallest {file_type} file: (No {file_type} files found)")
             print(f"\nLargest {file_type} file: (No {file_type} files found)")

    def print_summary(self):
        """Prints the final report."""
        print("\n\n--- Gopher Indexing Report ---")
        print(f"Server: {self.start_host}:{self.start_port}")
        print("-" * 30)

        print(f"1. Total Gopher directories found: {self.stats['dir_count']}")

        self._print_file_stats('text')

        self._print_file_stats('binary')

        # Invalid References
        invalid_refs = self.stats['invalid_references']
        print(f"\n8. Invalid references (type '3'): {len(invalid_refs)}")
        if invalid_refs:
            print("   List of unique invalid reference selectors:")
            for selector in sorted(list(set(invalid_refs))): # Unique selectors
                print(f" - '{selector}'")

        # External Servers
        print(f"\n9. External server references found: {len(self.external_servers)}")
        if self.external_servers:
            print("   List of external servers (host, port) and status:")
            for (host, port), status in sorted(self.external_servers.items()):
                print(f" - {host}:{port} -> {status.upper()}")

        # Request Errors
        req_errors = self.stats['request_errors']
        print(f"\n10. Requests with errors (timeout, network, parsing, etc.): {len(req_errors)}")
        if req_errors:
            print(" List of unique selectors/items with errors:")
            for error_item in sorted(list(set(req_errors))): # Unique items
                print(f" - '{error_item}'")

        print("\n--- End of Report ---")

# --- Main Execution ---
if __name__ == "__main__":
    target_host = "comp3310.ddns.net"
    target_port = DEFAULT_GOPHER_PORT

    if len(sys.argv) > 1: target_host = sys.argv[1]
    if len(sys.argv) > 2:
        try: target_port = int(sys.argv[2])
        except ValueError: print(f"Error: Invalid port '{sys.argv[2]}'. Using default {DEFAULT_GOPHER_PORT}.", file=sys.stderr)

    # Perform initial request manually for Wireshark capture
    print("\n--- Performing initial request for Wireshark capture ---")
    initial_response_bytes = connect_and_request(target_host, target_port, '') # Request root
    if initial_response_bytes is not None:
        print("--- Initial request successful. Received response. ---")
        try:
            initial_response_text = GopherCrawler(target_host, target_port)._decode(initial_response_bytes)
            print("--- Start of Initial Response (first 5 lines) ---")
            print("\n".join(initial_response_text.splitlines()[:5]))
            print("--- End of Initial Response ---")
        except Exception as e: print(f"Could not decode initial response for display: {e}", file=sys.stderr)
    else:
        print("--- Initial request FAILED. Cannot proceed with crawl. ---", file=sys.stderr)
        sys.exit(1)

    print("\n--- Initial request complete. Proceeding with full crawl... ---")
    time.sleep(2)

    crawler = GopherCrawler(target_host, target_port)
    try:
        crawler.crawl()
    except KeyboardInterrupt:
        print("\n--- Crawl interrupted by user ---")
    except Exception as e:
        print(f"\n--- An unexpected error occurred during crawl: {e} ---", file=sys.stderr)
        traceback.print_exc()
    finally:
        print("--- Printing Summary ---")
        crawler.print_summary()
