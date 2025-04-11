// src/main/java/com/example/chat/Client.java
// run the command:
// `mvn exec:java -Dexec.mainClass="com.example.chat.Client"`
// from the root directory to start the client

package com.example.chat;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.net.Socket;

// need two threads:
// one thread receives all the msgs from the server
// the other will receive console line inputs

public class Client implements Runnable {

  private Socket client;
  private BufferedReader input;
  private PrintWriter output;
  // running variable is accessed and modified by different
  // threads (main client thread/server-reader in run() and
  // the InputHandler thread). To ensure changes made by one
  // thread are immediately visible to the other, declare it
  // as volatile.
  private volatile boolean running;

  @Override
  public void run() {
    try {
      this.client = new Socket("127.0.0.1", 5000);
      output = new PrintWriter(this.client.getOutputStream(), true);
      input = new BufferedReader(new InputStreamReader(this.client.getInputStream()));

      running = true;

      // create threads
      InputHandler inputHandler = new InputHandler();
      Thread t = new Thread(inputHandler);
      t.start(); // start opens separate threads

      String inputMessage;
      while (running && (inputMessage = input.readLine()) != null) {
        System.out.println(inputMessage);
      }
    } catch (IOException e) {
      if (running) {
        System.err.println("Connection error: " + e.getMessage());
        shutdown();
      }
    } finally {
      // shutdown if loop finished normally (servre disconnect)
      // or if exception occurred before the catch block finished
      if (running) {
        shutdown();
      }
    }
  }

  public void shutdown() {
    if (!running)
      return;
    System.out.println("Shutting down client ...");
    running = false;
    try {
      // close streams
      if (input != null)
        input.close();
      if (output != null)
        output.close();
      // close socket
      if (this.client != null && !this.client.isClosed()) {
        this.client.close();
      }
    } catch (IOException e) {
      System.err.println("Error during client shutdown: " + e.getMessage());
      e.printStackTrace();
    }
  }

  class InputHandler implements Runnable {

    @Override
    public void run() {
      try {
        BufferedReader inputReader = new BufferedReader(new InputStreamReader(System.in));

        while (running) {
          String message = inputReader.readLine();
          if (message.equals("/quit")) {
            // shutdown client
            output.println(message);
            inputReader.close();
            shutdown();
          } else {
            // send message to server
            output.println(message);
          }
        }

      } catch (Exception e) {
        shutdown();
      }
    }
  }

  public static void main(String[] args) {
    Client client = new Client();
    client.run();
  }
}
