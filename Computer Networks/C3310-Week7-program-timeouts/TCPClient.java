/**
 * TCP echo client program for ANU COMP3310.
 *
 * Run with
 *     java TCPClient [address [port]]
 *
 * CC0: This code is dedicated to the public domain.
 * This code may be freely copied and modified for any purpose.
 * https://creativecommons.org/publicdomain/zero/1.0/
 *
 * @author Hugh Fisher (u9011925), ANU, 2024.
 * @author Felix Friedlander (u6675843), ANU, 2024.
 */

import java.io.*;
import java.net.*;

public class TCPClient {

	public static void main(String[] args) throws IOException {
		String serviceHost = "127.0.0.1";
		int servicePort = 3310;

		/*
		 * For arguments any more complicated than this,
		 * better to use a library.
		 */
		if (args.length > 0) {
			serviceHost = args[0];
			if (args.length > 1)
				servicePort = Integer.parseInt(args[1]);
		}

		loop(serviceHost, servicePort);
		System.out.println("Done.");
	}

	/**
	 * Read lines of input, send them to the echo server, and wait for
	 * and print the server's response.
	 */
	protected static void loop(String host, int port) throws IOException {
		Socket sock = new Socket(host, port);
		InetSocketAddress remote =
			(InetSocketAddress)sock.getRemoteSocketAddress();
		System.out.printf("Connected to %s:%d\n",
			remote.getAddress().getHostAddress(), remote.getPort());

		BufferedReader in =
			new BufferedReader(new InputStreamReader(sock.getInputStream()));
		PrintWriter out = new PrintWriter(sock.getOutputStream(), true);

		BufferedReader stdin =
			new BufferedReader(new InputStreamReader(System.in));

		while (true) {
			String line = stdin.readLine();
			if (line == null)
				break;

			sendRequest(out, line);
			readReply(in);
		}
		System.out.println("Closing socket");
		sock.close();
	}

	/**
	 * Send a request to the server.
	 */
	protected static void sendRequest(PrintWriter out, String request)
		throws IOException {

		out.println(request);
		System.out.println("Sent request to server...");
	}

	/**
	 * Read and print a response from the server.
	 */
	protected static void readReply(BufferedReader in) throws IOException {
		String reply = in.readLine();
		System.out.print("Received response: ");
		System.out.println(reply);
	}

}
