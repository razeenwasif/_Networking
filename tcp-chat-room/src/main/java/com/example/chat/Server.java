// src/main/java/com/example/chat/Server.java
// run the command:
// `mvn exec:java -Dexec.mainClass="com.example.chat.Server"`
// from the root directory to start the server

package com.example.chat;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

// Runnable allows the class to be passed to thread
// and can be run concurrently alongside other
// runnable classes
public class Server implements Runnable {

  // List of clients that are connected
  private ArrayList<ConnectionHandler> connections;
  private ServerSocket server;
  private boolean running;
  private ExecutorService threadPool;

  public Server() {
    connections = new ArrayList<>();
    running = true;
  }

  @Override
  // code in here will be executed when starting the class
  public void run() {
    try {
      // server will constantly listen for incoming connections
      // and accept the connection requests and open a new
      // connection handler for each client that connects.
      server = new ServerSocket(5000); // port
      threadPool = Executors.newCachedThreadPool();
      System.out.println("Server started on port 5000 ...");

      while (running) {
        // accepting client socket
        Socket client = server.accept();
        ConnectionHandler handler = new ConnectionHandler(client);
        connections.add(handler);
        threadPool.execute(handler);
      }
    } catch (Exception e) {
      shutdown();
    }
  }

  // broadcast to all the different clients that are connected
  public void broadcast(String message) {
    for (ConnectionHandler ch : connections) {
      if (ch != null) {
        ch.sendMessage(message);
      }
    }
  }

  // shutdown server
  public void shutdown() {
    try {
      running = false;
      threadPool.shutdown();
      if (!server.isClosed()) {
        server.close();
      }
      for (ConnectionHandler ch : connections) {
        ch.shutdown();
      }
    } catch (IOException e) {
      // ignore
    }
  }

  // inner class to handle client connections
  class ConnectionHandler implements Runnable {

    private Socket client;
    private BufferedReader input;
    private PrintWriter output;
    private String username;

    // handle multiple clients concurrently here
    public ConnectionHandler(Socket client) {
      this.client = client;
    }

    @Override
    public void run() {
      // initialize in and out streams
      try {
        output = new PrintWriter(client.getOutputStream(), true); // autoflush true
        input = new BufferedReader(new InputStreamReader(client.getInputStream()));

        output.println("Please enter a username: ");
        username = input.readLine();
        System.out.println(username + " connected");
        broadcast(username + " joined the chat");

        String message;
        // Some available user commands
        while ((message = input.readLine()) != null) {
          if (message.startsWith("/user ")) {
            // handle user name change
            String[] messageSplit = message.split(" ", 2);
            if (messageSplit.length == 2) {
              broadcast(username + " renamed themselves to " + messageSplit[1]);
              // first index will be "/user "
              username = messageSplit[1];
              output.println("Changed username to " + username);
            } else {
              output.println("No nickname provided");
            }
          } else if (message.startsWith("/quit")) {
            // allow client to quit
            broadcast(username + " left the chat");
            shutdown();
          } else {
            broadcast(username + ": " + message);
          }
        }

      } catch (IOException e) {
        shutdown();
      }
    }

    public void sendMessage(String message) {
      output.println(message);
    }

    // shutdown client when servre shutsdown
    public void shutdown() {
      try {
        input.close();
        output.close();
        if (!client.isClosed()) {
          client.close();
        }
      } catch (IOException e) {
        System.out.println("Server.ConnectionHandler.shutdown()");
      }
    }
  }

  public static void main(String[] args) {
    Server server = new Server();
    server.run();
  }
}
