
import asyncio
from websockets.sync.client import connect
import time

ADDRESS = '192.168.86.50:7891'

def hello():
    with connect("ws://" + ADDRESS) as websocket:
        while True:
            websocket.send("imu/orientation_x")
            message = websocket.recv()
            print(f"Received: {message}")
            time.sleep(1/10.0)

hello()
