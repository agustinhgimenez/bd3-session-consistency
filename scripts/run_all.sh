#!/usr/bin/env bash
set -e
python3 nodes/nodo_1.py &
python3 nodes/nodo_2.py &
python3 nodes/nodo_3.py &
wait
