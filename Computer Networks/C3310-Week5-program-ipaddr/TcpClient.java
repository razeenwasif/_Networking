
/** TCP echo client program for ANU COMP3310.
 *
 *  Run with
 *      java TcpClient [ IP addr ] [ port ]
 *
 *  Written by Hugh Fisher u9011925, ANU, 2024
 *  Released under Creative Commons CC0 Public Domain Dedication
 *  This code may be freely copied and modified for any purpose
 */


import java.io.*;
import java.net.*;


public class TcpClient {

    //  IP address and port that client will contact
    static String   serviceHost = "127.0.0.1";
    static int      servicePort = 3310;

    /** Read input until EOF. Send as request to host, print response */

    protected static void inputLoop(String host, int port)
        throws IOException
    {
        Socket              sock;
        BufferedReader      input;
        String              line, reply;
        InetSocketAddress   remote;

        // Create TCP socket, connected to a single host
        sock = new Socket(host, port);
        remote = (InetSocketAddress) sock.getRemoteSocketAddress();
        System.out.printf("Client connected to %s %d\n",
                            remote.getAddress().getHostAddress(), remote.getPort());
        // Keep reading lines and sending them
        input = new BufferedReader(new InputStreamReader(System.in));
        while (true) {
            line = input.readLine();
            if (line == null)
                break;
            sendRequest(sock, line);
            readReply(sock);
        }
        System.out.println("Client close");
        // Tell the server we are done
        SockLine.writeLine(sock, "BYE");
        sock.close();
    }

    /** Send our request to server */

    protected static void sendRequest(Socket sock, String request)
        throws IOException
    {
        // No try: if anything goes wrong, higher level will handle
        SockLine.writeLine(sock, request);
        System.out.println("Sent request to server");
    }

    /** Read and print server response */

    protected static void readReply(Socket sock)
        throws IOException
    {
        String          reply;

        reply = SockLine.readLine(sock);
        System.out.println(reply);
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
