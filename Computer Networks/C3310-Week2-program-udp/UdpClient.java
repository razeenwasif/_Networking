
/** UDP echo client program for ANU COMP3310.
 *
 *  This is the other half of a client-server architecture.
 *  The client knows the server, and makes requests to get a response.
 *
 *  Run with
 *      java UdpClient [ IP addr ] [ port ]
 *
 *  Written by Hugh Fisher u9011925, ANU, 2024
 *  Released under Creative Commons CC0 Public Domain Dedication
 *  This code may be freely copied and modified for any purpose
 */


import java.io.*;
import java.net.*;


public class UdpClient {

    //  IP address and port that client will contact
    static String   serviceHost = "127.0.0.1";
    static int      servicePort = 3310;

    // Our maximum UDP data size, in bytes.
    // Absolute maximum for UDP would be 64K, but reliability goes down a lot
    // for packets larger than 1K or so, and more than 8K is unlikely.
    static final int    MSG_MAX = 1024;

    // Maximum time to wait for a reply, in millisecs
    static final int    TIMEOUT = 4000;


    /** Read input until EOF. Send as request to host, print response */

    protected static void inputLoop(String host, int port)
        throws IOException
    {
        DatagramSocket      sock;
        BufferedReader      input;
        String              line, reply;
        InetSocketAddress   remote;

        // Create an Internet UDP socket
        sock = new DatagramSocket();
        // This client will only connect to a single server, so we can set the peer
        // address, ie the remote server, for this socket just once.
        sock.connect(new InetSocketAddress(host, port));
        remote = (InetSocketAddress) sock.getRemoteSocketAddress();
        System.out.printf("Client created socket to %s %d\n",
                            remote.getAddress().getHostAddress(), remote.getPort());
        // UDP, like IP, is not a reliable protocol so we can't guarantee packets get
        // there, and in fact we can't even be sure that there is a server! This is
        // the maximum time to wait for a reply. (Also the maximum time to wait when
        // trying to send, but that usually is not a problem.)
        sock.setSoTimeout(TIMEOUT);
        // Now keep reading lines and sending them
        input = new BufferedReader(new InputStreamReader(System.in));
        while (true) {
            line = input.readLine();
            if (line == null)
                break;
            sendRequest(sock, line);
            System.out.println("Sent request to server");
            reply = readReply(sock);
            if (reply == null)
                System.out.println("TIME OUT");
            else
                System.out.println(reply);
        }
        System.out.println("Client close");
        sock.close();
    }

    /** Send our request to server */

    protected static void sendRequest(DatagramSocket sock, String request)
        throws UnsupportedEncodingException, IOException
    {
        byte[]          outData;
        DatagramPacket  packet;

        // Like the server, encoding into wire format is done at the last moment
        outData = request.getBytes("UTF-8");
        // Our client socket is already connected to the server address
        packet = new DatagramPacket(outData, outData.length, sock.getRemoteSocketAddress());
        // and send
        sock.send(packet);
    }

    /** Read string and return, or null if the socket times out */

    protected static String readReply(DatagramSocket sock)
        throws IOException
    {
        DatagramPacket  packet;
        String          reply;

        // Socket is permanently connected so we know who it came from.
        packet = new DatagramPacket(new byte[MSG_MAX], MSG_MAX);
        try {
            sock.receive(packet);
        } catch (SocketTimeoutException e) {
            return null;
        }
        // We hope the server sent us UTF-8, but don't count on it
        try {
            reply = new String(packet.getData(), 0, packet.getLength(), "UTF-8");
        } catch (UnsupportedEncodingException e) {
            // Not UTF-8 :-(
            System.out.println("Unable to decode UTF-8 string");
            reply = "????";
        }
        return reply;
    }


    /** Handle command line arguments. */

    protected static void processArgs(String[] args)
    {
        //  This program has only two CLI arguments, and we know the order.
        //  For any program with more than two args, use a loop or package.
        if (args.length > 0) {
            serviceHost = args[0];
            if (args.length > 1) {
                servicePort = Integer.parseInt(args[1]);
            }
        }
    }

    public static void main(String[] args)
    {
        try {
            processArgs(args);
            inputLoop(serviceHost, servicePort);
            System.out.println("Done.");
        } catch (Exception e) {
            System.out.println(e.toString());
            System.exit(-1);   
        }
    }

}
