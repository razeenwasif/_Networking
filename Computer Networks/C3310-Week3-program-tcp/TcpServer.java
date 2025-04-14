
/** TCP echo server program for ANU COMP3310.
 *
 *  Run with
 *      java TcpServer [ port ]
 *
 *  Written by Hugh Fisher u9011925, ANU, 2024
 *  Released under Creative Commons CC0 Public Domain Dedication
 *  This code may be freely copied and modified for any purpose
 */


import java.io.*;
import java.net.*;


public class TcpServer {

    // IP port only, we are using Java built in server socket class
    static int      servicePort = 3310;

    /** Accept client connections on given port */

    protected static void clientLoop(int port)
        throws IOException, SocketException
    {
        ServerSocket        serverSock;
        Socket              client;
        InetSocketAddress   remote;

        // Create TCP socket, for server bound to given port on 0.0.0.0
        // and with whatever listen value seems right.
        serverSock = new ServerSocket(port);
        //  If you really want to specify hostname/interface and listen,
        //  serverSock = new ServerSocket(port, 5, InetAddress.getByName(serviceHost))
        // Servers should set this option which allows them to be re-run immediately.
        // If you don't, you may have to wait a few minutes before restarting the server.
        serverSock.setReuseAddress(true);
        System.out.printf("Created server socket for %s %d\n",
                            serverSock.getInetAddress().getHostAddress(),
                            serverSock.getLocalPort());
        while (true) {
            // A TCP server is different to UDP. Instead of packets,
            // we get connection requests from clients.
            try {
                client = serverSock.accept();
            } catch (IOException e) {
                // If something goes wrong with the network, we will stop
                System.out.printf("%s in clientLoop\n", e.toString());
                break;
            }
            remote = (InetSocketAddress) client.getRemoteSocketAddress();
            System.out.printf("Accepted client connection from %s %d\n",
                            remote.getAddress().getHostAddress(), remote.getPort());
            // Each connection accepted creates a new socket for that
            // particular client. Use for requests and replies.
            serverLoop(client);
            // We don't get back here until the client session ends
        }
        System.out.println("Close server socket");
        serverSock.close();
    }

    /** Echo service for a single client */

    protected static void serverLoop(Socket sock)
        throws IOException
    {
        String request;

        // Read and respond until client shuts down the socket,
        // using shared line read/write code
        while (true) {
            try {
                request = SockLine.readLine(sock);
                if (request == null)
                    break;
                System.out.printf("Server received %s", request);
                handleRequest(sock, request);
            } catch (IOException e) {
                // Try not to crash if the client does something wrong
                System.out.printf("%s in serverLoop\n", e.toString());
                break;
            }
        }
        System.out.println("Close client socket");
        sock.close();
    }

    /** Respond to one client request */

    protected static void handleRequest(Socket sock, String message)
        throws IOException
    {
        String reply = "ACK: " + message;
        System.out.printf("Server sending reply %s\n", reply);
        SockLine.writeLine(sock, reply);
    }


    /** Handle command line argument. */

    protected static void processArgs(String[] args)
    {
        //  Only port number for Java server.
        if (args.length > 0) {
            servicePort = Integer.parseInt(args[1]);
        }
    }

    public static void main(String[] args)
    {
        try {
            processArgs(args);
            clientLoop(servicePort);
            System.out.println("Done.");
        } catch (Exception e) {
            System.out.println(e.toString());
            System.exit(-1);   
        }
    }

}
