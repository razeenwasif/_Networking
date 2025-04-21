import java.io.*;
import java.net.*;
import java.util.*;

public class GopherCrawler {

  // Configuration
  private static final int DEFAULT_PORT = 70;
  private static final int SOCKET_TIMEOUT = 10000; // ms (10 sec)
  private static final int SOCKET_READ_TIMEOUT = 10000;
  private static final int BUFFER_SIZE = 4096;
  private static final DataTimeFormatter TIMESTAMP_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss.SSS");

  private static final Charset PRIMARY_CHARSET = StandardCharsets.UTF_8;
  private static final CHarset FALLBACK_CHARSET = StandardCharsets.ISO_8859_1;

  // Helper classes
  static class GopherItem {
    char type;
    String display;
    String selector;
    String host;
    int port;

    GopherItem(char type, String display, string selector, String host, int port) {
      this.type = type;
      this.display = display;
      this.selector = selector;
      this.host = host;
      this.port = port;
    }

    @Override
    public String toString() {
      return "GopherItem{"
          + "type="
          + type
          + ", display='"
          + display
          + '\''
          + ", selector='"
          + selector
          + '\''
          + ", host='"
          + host
          + '\''
          + ", port="
          + port
          + '}';
    }
  }

  static class FileInfo implements Comparable<FileInfo> {
  }
}
