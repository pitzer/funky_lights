import crc8
import serial
import time
import sys
import asyncio
import websockets

NUM_LEDS = 30
MAGIC = 0x55
CMD_LEDS = 1
WEB_SOCKET_PORT = 5678
uid = 1

def RgbToBits(rgbs):
  """ Convert RGB value given as a 3-tuple to a list of two bytes that can
       be sent to the LEDs. We pack data as 16 bits:
         RRRRRGGGGGGBBBBB
  Args:
   rgbs: list of rgb tuples
  Returns:
   a list of bytes
  """
  out = []
  for rgb in rgbs:
    r, g, b = rgb
    out += [((g << 3) & 0xE0) | ((b >> 3) & 0x1F), (r & 0xF8) | ((g >> 5) & 0x07)]
  return out

def PrepareLedMsg(bar_uid, rgbs):
  """ Prepare a message from a list of RGB colors
  Args:
   serial: Serial port object. Should be already initialized
   bar_uid: UID of the bar to which we want to send the message
   rgbs: list of rgb tuples
  Returns:
   a bytearray, ready to send on the serial port
  """
  header = [MAGIC, bar_uid, CMD_LEDS]
  data = RgbToBits(rgbs)
  crc_compute = crc8.crc8()
  crc_compute.update(bytearray(data))
  crc = [crc_compute.digest()[0]]
  msg = header + data + crc
  return bytearray(msg)

async def serve(websocket, path):
  # Create test pattern
  rgbs = []
  for i in range(int(NUM_LEDS / 2)):
    col = int(i / (NUM_LEDS / 2) * 255)
    rgbs += [(col, 255-col, 0)]
  for i in range(int(NUM_LEDS / 2)):
    col = int(255 - (i / (NUM_LEDS / 2) * 255))
    rgbs += [(col, 255 - col, 0)]

  # Serve patterns
  while True:
    msg = PrepareLedMsg(uid, rgbs)
    rgbs = rgbs[1:] + rgbs[:1]

    try:
      await websocket.send(msg)
      await asyncio.sleep(0.05)
    except websockets.ConnectionClosed as exc:
      break
    
def main():
  if len(sys.argv) > 1:
      uid = int(sys.argv[1])

  # Send messages to all the bars
  start_server = websockets.serve(serve, '127.0.0.1', WEB_SOCKET_PORT)
  asyncio.get_event_loop().run_until_complete(start_server)
  asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    main()