#!/bin/bash 
echo "Starting 10 MQTT publishers ..."
for i in $(seq -f "%02g" 1 10); do 
  echo "Launching pub-${i}"
  python publisher.py "pub-${i}" & # '&' runs it in background 
  sleep 0.2 
done 
echo "All publisher processes launched in the background."
echo "Use 'pkill -f \"python publisher.py\"' or similar to stop them later."
