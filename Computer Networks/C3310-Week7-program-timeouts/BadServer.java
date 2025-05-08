/**
 * Flaky TCP echo server program for ANU COMP3310.
 *
 * Run with
 *     java BadServer [port]
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

public class BadServer {

	public static void main(String[] args)
		throws IOException, SocketException {

		int servicePort = 3310;
		if (args.length > 0)
			servicePort = Integer.parseInt(args[0]);

		serverLoop(servicePort);
		System.out.println("Done.");
	}

	/**
	 * Accept client connections on the given port.
	 */
	protected static void serverLoop(int port)
		throws IOException, SocketException {

		ServerSocket server = new ServerSocket(port);
		server.setReuseAddress(true);

		System.out.printf("Server listening on %s:%d\n",
			server.getInetAddress().getHostAddress(),
			server.getLocalPort());

		Socket client;
		while (true) {
			try {
				client = server.accept();
			} catch (IOException e) {
				System.out.printf("serverLoop: %s\n", e.toString());
				break;
			}
			InetSocketAddress remote =
				(InetSocketAddress)client.getRemoteSocketAddress();
			System.out.printf("Accepted client connection from %s:%d\n",
				remote.getAddress().getHostAddress(), remote.getPort());
			clientLoop(client);
		}
		System.out.println("Closing server socket");
		server.close();
	}

	/**
	 * Flaky echo service for a single client; doesn't respond sometimes.
	 */
	protected static void clientLoop(Socket sock)
		throws IOException {

		/* Keep track of the number of requests we've seen */
		int requests = 0;

		BufferedReader in =
			new BufferedReader(new InputStreamReader(sock.getInputStream()));
		PrintWriter out = new PrintWriter(sock.getOutputStream(), true);

		while (true) {
			try {
				String request = in.readLine();
				if (request == null)
					break;
				System.out.printf("Received: %s\n", request);

				/*
				 * Don't respond to a request if the request count
				 * is a multiple of 3 (i.e. every third request)
				 */
				if ((++requests) % 3 == 0) {
					System.out.println("Not responding >:)");
				} else {
					String response = "ACK " + request;

					out.println(response);
					System.out.print("Sent: ");
					System.out.println(response);
				}
			} catch (IOException e) {
				/* Try not to crash if the client does something wrong */
				System.out.printf("clientLoop: %s\n", e.toString());
				break;
			}
		}
		System.out.println("Closing client socket");
		sock.close();
	}

}
