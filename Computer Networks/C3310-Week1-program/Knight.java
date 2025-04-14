
/** COMP3310 Tute 0 programming warmup exercise.
 *  Second of two programs.
 *  Compile with
 *      javac Knight.java
 *  Run with
 *      java Knight
 *
 *  Written by Hugh Fisher u9011925, ANU, 2024
 *  Released under Creative Commons CC0 Public Domain Dedication
 *  This code may be freely copied and modified for any purpose
 */

import java.io.*;

public class Knight {

    /** Read input until EOF. Response depends on input. */

    protected static void inputLoop()
        throws IOException
    {
        BufferedReader input;
        String line, response;

        input = new BufferedReader(new InputStreamReader(System.in));
        while (true) {
            line = input.readLine();
            // Java Reader just returns null on EOF, not an exception
            if (line == null)
                break;
            chooseResponse(line);
        }
        input.close();
    }

    /** Decide what to print based on input line. */

    protected static void chooseResponse(String line)
    {
        if (line.equals("it")) {
            // Crash
            throw new RuntimeException("Aaargh! You said it!");
        } else if (line.equals("ni")) {
            // Go into infinite loop
            while (true) {
                System.out.println("Ni! Ni! Ni!");
            }
        } else {
            System.out.println(line);
        }
    }


    /** No command line arguments. */

    protected static void processArgs(String[] args)
    {
        if (args.length > 0) {
            throw new RuntimeException("No command line arguments");
        }
    }

    public static void main(String[] args)
    {
        // Java, unlike Python, insists we handle all exceptions
        try {
            processArgs(args);
            inputLoop();
            System.out.println("Done.");
        } catch (Exception e) {
            System.out.println(e.toString());
            System.exit(-1);   
        }
    }

}
