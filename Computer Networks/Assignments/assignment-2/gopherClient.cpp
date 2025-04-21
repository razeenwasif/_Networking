#include <iostream>
#include <string>
#include <vector>
#include <queue>
#include <set>
#include <map>
#include <sstream>
#include <chrono>
#include <ctime> 
#include <iomanip>
#include <limits>
#include <stdexcept>
#include <algorithm>
#include <optional>

// for linux
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <unistd.h>
#include <cerrno>
#define SOCKET_TYPE int 
#define INVALID_SOCKET_VAL -1
#define GET_LAST_ERROR errno 

///////////////// Configuration ///////////////

const int DEFAULT_PORT = 70;
const int SOCKET_TIMEOUT = 10;
const int BUFFER_SIZE = 4096;

//////////////// Helper Structs ///////////////

struct GopherItem {
  char type = '\0';
  std::string display;
  std::string selector;
  std::string host;
  int port = 0;
  // check for successful parsing
  bool valid = false; 
};

struct FileInfo {
  std::string selector;
  size_t size = 0;

  bool operator<(const FileInfo& other) const {
    return selector < other.selector;
  }
};

/////////////// Helper Functions /////////////

// Utility to split string by delimiter 
std::vector<std::string> split_string(
  const std::string& s, char delimiter
) {
  std::vector<std::string> tokens;
  std::string token;
  std::isstringstream tokenStream(s);
  while (std::getline(
    tokenStream, token, delimiter
  )) {
    tokens.push_back(token);
  }
  return tokens;
}

// Trim whitespace from start and end of string
std::string trim_string(const std::string& str) {
  size_t first = str.find_first_not_of(" \t\r\n");
  if (std::string::npos == first) {
    return str;
  }
  size_t last = str.find_last_not_of(" \t\r\n");
  return str.substr(first, (last - first + 1));
}

void log_request(const std::string& selector) {
  auto now = std::chrono::system_clock::now();
  auto ms = std::chrono::duration_cast<
      std::chrono::milliseconds
    >(now.time_since_epoch()) % 1000;
  auto timer = 
    std::chrono::system_clock::to_time_t(now);
  std::tm bt = *std::localtime(&timer);
  std::cout << std::put_time(
    &bt, "%Y-%m-%d %H:%M:%S"
  );
  std::cout << '.' << std::setfill('0') << std::setw(3) << ms.count();

  std::string printable_selector = selector;
  if (printable_selector.empty()) {
    printable_selector = "(root selector)";
  }
  // Replace non-printable characters for logging
  std::cout << "Requesting selector: '" << printable_selector << "'" << std::endl;
}

// Parses a single line from the Gopher dir list 
std::optional<GopherItem> parse_gopher_line(
  const std::string& line
) {
  if (line.empty() || line.length() < 1) {
    return std::nullopt;
  }
  GopherItem item;
  item.type = line[0];
  std::string rest = line.substr(1);

  std::vector<std::string> parts = 
    split_string(rest, '\t');

  if (parts.size() < 4) {
    // handle informational messages ('i') which
    // might not have all parts
    if (item.type == 'i' && parts.size() >= 1) {
      item.display = trim_string(parts[0]);
      item.selector = ""; // no action
      item.host = "";
      item.port = 0;
      item.valid = true;
      return item;
    }
    return std::nullopt; // malformed line 
  }

  item.display = trim_string(parts[0]);
  item.selector = trim_string(parts[1]);
  item.host = trim_string(parts[2]);
  std::string port_str = trim_string(parts[3]);

  try {
    item.port = std::stoi(port_str);
  } catch (const std::invalid_argument& ia) {
    return std::nullopt;
  } catch (const std::out_of_range& oor) {
    return std::nullopt;
  }

  item.valid = true;
  return item;
}

/////// socket initialization / cleanup ////////

// error message helper
std::string get_socket_error_message() {
  return std::string(strerror(GET_LAST_ERROR)) + "(Code: " + std::to_string(GET_LAST_ERROR) + ")";"
}

// Connects, sends request, receives response.
// returns response as vector<char> or 
// nullopt on error 
std::optional<std::vector<char>>
  connect_and_request(
  const std::string& host, 
  int port, 
  const std::string& selector
) {
  log_request(selector);
  SOCKET_TYPE sock = INVALID_SOCKET_VAL;
  struct addrinfo hints = {}, *servinfo = nullptr, *p = nullptr;
  std::vector<char> response_data;

  // Resolve hostname & Get Address info 
  memset(&hints, 0, sizeof hints);
  hints.ai_family = AF_UNSPEC; // allow ipv4 or 6 
  hints.ai_socktype = SOCK_STREAM;
  hints.ai_protocol = IPPROTO_TCP;

  std::string port_str = std::to_string(port);
  if (getaddrinfo(host.c_str(), port_str.c_str(), &hints, &servinfo) != 0) {
    std::cerr << "Error: getaddrinfo faled for host '" << host << "': " << get_socket_error_message() << std::endl;
    return std::nullopt;
  }

  // create socket and connect 
  for (p = servinfo; p != nullptr; p = p -> ai_next) {
    sock = socket(p -> ai_family, p -> ai_socktype, p -> ai_protocol);
    if (sock == INVALID_SOCKET_VAL) {
      continue;
    }

    // set timeout 
    struct timeval tv;
    tv.tv_sec = SOCKET_TIMEOUT;
    tv.tv_usec = 0;
    if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, (const void*)&tv, sizeof(tv)) < 0 || setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, (const void*)&tv, sizeof(tv)) < 0) {
      std::cerr << "Warning: setsockopt(SO_RCVTIMEO/SO_SNDTIMEO) failed: " << get_socket_error_message() << std::endl;
    }

    // Connect 
    if (connect(sock, p->ai_addr, (int)p->ai_addrlen) == -1) {
      int connect_errno = GET_LAST_ERROR;
      if (connect_errno != ETIMEDOUT && connect_errno != ECONNREFUSED) {
        std::cerr << "Warning: connect() failed: " << get_socket_error_message() << std::endl;
      }
      close(sock);
      sock = INVALID_SOCKET_VAL;
      continue;
    }
    break; // successfully connected 
  }
  freeaddrinfo(servinfo); // free the linked list 
  
  if (p == nullptr) {
    std::cerr << "Error: Failed to connect to " << host << ":" << port << " (tried all addresses)" << std::endl;
        return std::nullopt;
  }
  
  // Send Request 
  std::string request_str = selector + "\r\n";
  int bytes_sent = send(sock, request_str.c_str(), (int)request_str.length(), 0);
  if (bytes_sent == -1) {
      std::cerr << "Error: send() failed: " << get_socket_error_message() << std::endl;
      close(sock);
      return std::nullopt;
  }
  if (bytes_sent != (int)request_str.length()) {
        std::cerr << "Warning: Could not send full request (" << bytes_sent << "/" << request_str.length() << ")" << std::endl;
        // Potentially problematic, but continue to try receiving
  }


  // --- 6. Receive Response ---
  char buffer[BUFFER_SIZE];
  int bytes_received;
  while (true) {
    bytes_received = recv(sock, buffer, BUFFER_SIZE, 0);
    
    if (bytes_received > 0) {
        response_data.insert(response_data.end(), buffer, buffer + bytes_received);
    } else if (bytes_received == 0) {
        // Connection closed gracefully by peer
        break;
    } else { // bytes_received < 0 indicates an error
      int recv_error = GET_LAST_ERROR;
      #ifdef _WIN32
        if (recv_error == WSAETIMEDOUT) {
            std::cerr << "Error: Socket timeout receiving data from " << host << ":" << port << " for selector '" << selector << "'" << std::endl;
        } else {
            std::cerr << "Error: recv() failed: " << get_socket_error_message() << std::endl;
        }
      #else // POSIX
        if (recv_error == EAGAIN || recv_error == EWOULDBLOCK) { // These map to timeout with SO_RCVTIMEO
            std::cerr << "Error: Socket timeout receiving data from " << host << ":" << port << " for selector '" << selector << "'" << std::endl;
        } else {
            std::cerr << "Error: recv() failed: " << get_socket_error_message() << std::endl;
        }
      #endif
      close(sock);
      return std::nullopt; // Indicate error
    }
  }

  close(sock); // Close socket after receiving all data or error

  // --- 7. Check for Gopher directory termination sequence ".\r\n" ---
  // This is tricky with binary data, convert only the end part carefully if needed.
  // Let's check the raw bytes.
  const char* term1 = "\r\n.\r\n"; // 5 bytes
  const char* term2 = "\n.\n";   // 3 bytes
  const char* term3 = ".\r\n";   // 3 bytes (less common, but possible)

  if (response_data.size() >= 5 &&
      std::equal(response_data.end() - 5, response_data.end(), term1)) {
        response_data.resize(response_data.size() - 5);
  } else if (response_data.size() >= 3 &&
              std::equal(response_data.end() - 3, response_data.end(), term2)) {
        response_data.resize(response_data.size() - 3);
  } else if (response_data.size() >= 3 &&
              std::equal(response_data.end() - 3, response_data.end(), term3)) {
      response_data.resize(response_data.size() - 3);
  }

  return response_data;
}

////////////// Main Crawler Class //////////////
