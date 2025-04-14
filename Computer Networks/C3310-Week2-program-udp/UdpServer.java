
/** UDP echo server program for ANU COMP3310.
 *
 *  This is one half of a traditional Internet client-server architecture.
 *  As a server this program is expected to run (more or less) all the
 *  time, and handle requests from any client that connects.
 *
 *  Run with
 *      java UdpServer [ IP addr ] [ port ]
 * 
 *  Written by Hugh Fisher u9011925, ANU, 2024
 *  Released under Creative Commons CC0 Public Domain Dedication
 *  This code may be freely copied and modified for any purpose
 */

import java.io.*;
import java.net.*;


public class UdpServer {

    //  IP address and port that server reads requests from.
    //  Client needs to know these to connect.
    static String   serviceHost = "127.0.0.1";
    static int      servicePort = 3310;

    //  Maximum client request size, in bytes
    static final int    MSG_SIZE = 16;      // Do not copy this


    /** Python can return two values at a time, Java cannot */
    private static class SDU {
        // Do not copy this
        public DatagramPacket   dgram;
        public String           text;   // Java form of dgram data
    }


    /** Run echo service on given host and port */

    protected static void serverLoop(String host, int port)
        throws IOException
    {
        DatagramSocket  sock;
        SDU             request;

        // Create and Internet UDP socket and set the address and port that we read requests from
        sock = new DatagramSocket(new InetSocketAddress(host, port));
        System.out.printf("Server created socket for %s %d\n",
                            sock.getLocalAddress().getHostAddress(), sock.getLocalPort());
        // And now read and respond forever
        while (true) {
            try {
                request = readRequest(sock);
                replyToMessage(sock, request.text, request.dgram.getSocketAddress());
            } catch (IOException e) {
                break;
            }
        }
        System.out.println("Server close");
        sock.close();
    }

    /** Read a string up to predefined limit. Return string and original packet with client address */

    protected static SDU readRequest(DatagramSocket sock)
        throws IOException
    {
        DatagramPacket  packet;
        SDU             result;

        result = new SDU();
        // In UDP we usually don't have a permanent connection to the client, so we
        // read a network packet (up to limit) AND address of where it came from.
        packet = new DatagramPacket(new byte[MSG_SIZE], MSG_SIZE);
        sock.receive(packet);
        result.dgram = packet;
        // The data is just bytes. We hope it is a UTF-8 string, the Internet standard
        // for sending text, but Java uses a different format internally.
        // Internet programs should decode network data as soon as received.
        try {
            result.text = new String(packet.getData(), 0, packet.getLength(), "UTF-8");
        } catch (UnsupportedEncodingException e) {
            // Not UTF-8 :-(
            System.out.println("Unable to decode UTF-8 string");
            result.text = "????";
        }
        return result;
    }

    /** Generate reply to message */

    protected static void replyToMessage(DatagramSocket sock, String message, SocketAddress sender)
        throws IOException
    {
        String reply;

        // TODO: change behaviour depending on message
        reply = "ACK " + message;
        System.out.printf("Server sending reply %s\n", reply);
        sendReply(sock, reply, sender);
    }


    /** Send complete reply to client */

    protected static void sendReply(DatagramSocket sock, String text, SocketAddress sender)
        throws UnsupportedEncodingException, IOException
    {
        byte[]          outData;
        DatagramPacket  reply;

        // UDP packets are raw bytes so text should be UTF-8, the "wire format".
        // Encoding is usually done just before sending so the rest of the program
        // doesn't need to worry about what packets look like.
        outData = text.getBytes("UTF-8");
        // Create a new packet, same address as original request
        reply = new DatagramPacket(outData, outData.length, sender);
        // and send
        sock.send(reply);
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
            serverLoop(serviceHost, servicePort);
            System.out.println("Done.");
        } catch (Exception e) {
            System.out.println(e.toString());
            System.exit(-1);   
        }
    }

}
