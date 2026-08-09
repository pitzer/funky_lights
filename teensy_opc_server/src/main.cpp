// Open Pixel Control server for the Funklet Teensy 4.1 LED boards.
//
// Reconstructed from the controller side (controller/core/opc.py) and the
// configs, because the original firmware is not in this repository. Verify the
// items marked VERIFY below against a working board before trusting it.
//
// Wire protocol (http://openpixelcontrol.org/):
//   byte 0   channel   0 = broadcast to all, 1..8 = one strip
//   byte 1   command   0 = set pixel colours
//   byte 2   length high byte      length is in BYTES, = num_leds * 3
//   byte 3   length low byte
//   then     R,G,B per LED
//
// The controller sends all of a board's channels concatenated in a single
// write per frame, so several messages usually arrive in one TCP segment. We
// parse the stream continuously and latch to the LEDs once the socket drains,
// which batches a frame into one show().
//
// Build: PlatformIO. `pio run -e board2 -t upload` -- see platformio.ini.

#include <Arduino.h>
#include <OctoWS2811.h>
#include <QNEthernet.h>

using namespace qindesign::network;

// ---------------------------------------------------------------- board id --
//
// Each board answers on its own static address and serves its own set of
// segments. Set BOARD to 1 or 2 to build for that board.
//
// The controller maps OPC channel = (index of uid in bus_config.json) + 1,
// which matches the "Board position" column of the wiring table.
//
// Set by the build env: `pio run -e board1` or `-e board2` passes -D BOARD.
// The default below applies only if something builds this without that flag.

#ifndef BOARD
  #define BOARD 2
#endif

#if BOARD == 1
  static const uint8_t  kLastOctet   = 4;      // 192.168.1.4
  static const uint8_t  kNumChannels = 6;
  // ch:      1    2    3    4    5    6
  // uid:    12  114   17   18   16  271
  // seg:  tail  lfr  lbr  lfl  lbl  eyes_right
  static const uint16_t kChannelLen[kNumChannels] = { 54, 74, 80, 82, 89, 256 };
#elif BOARD == 2
  static const uint8_t  kLastOctet   = 5;      // 192.168.1.5
  static const uint8_t  kNumChannels = 8;
  // ch:      1    2    3    4    5    6    7    8
  // uid:    21  214  272   28   26  220  221   25
  // seg:  dome ball eyes_left tusks ear_l trunk ear_r head
  static const uint16_t kChannelLen[kNumChannels] = { 181, 33, 256, 2, 68, 134, 69, 65 };
#else
  #error "Set BOARD to 1 or 2"
#endif

// --------------------------------------------------------------- constants --

static const uint16_t kOpcPort = 7890;

// OctoWS2811 drives all eight outputs in lockstep, so every strip is allocated
// the length of the longest one. Unused tail pixels stay dark.
static const uint16_t kLedsPerStrip = 256;
static const uint8_t  kNumStrips    = 8;

// VERIFY: colour order. The strips are WS2811. The controller sends R,G,B in
// that order and no longer applies any per-segment correction, so if colours
// come out wrong here this is the constant to change (WS2811_RGB, WS2811_GRB,
// WS2811_BRG, ...). Note the tusks previously had a green/blue swap applied on
// the controller side, which suggests that strip may not match the others -- if
// only the tusks are wrong, the fix belongs in the wiring or in a per-channel
// swap rather than here.
static const int kLedConfig = WS2811_GRB | WS2811_800kHz;

// Two limits. A per-channel message can never exceed one strip; a channel-0
// broadcast legitimately carries every strip end to end, so the buffer has to
// be big enough for that or the tail of a broadcast is silently discarded.
static const uint16_t kMaxChannelPayload = kLedsPerStrip * 3;                 //  768
static const uint16_t kMaxPayload        = kNumStrips * kLedsPerStrip * 3;    // 6144

// ------------------------------------------------------------------ globals --

DMAMEM int displayMemory[kLedsPerStrip * 6];
int        drawingMemory[kLedsPerStrip * 6];

OctoWS2811 leds(kLedsPerStrip, displayMemory, drawingMemory, kLedConfig);
EthernetServer server(kOpcPort);
EthernetClient client;

// OPC stream parser state. TCP is a byte stream, so a message can be split
// across reads and several can arrive together -- neither can be assumed.
enum ParseState { WAIT_HEADER, READ_PAYLOAD, SKIP_PAYLOAD };
static ParseState state = WAIT_HEADER;
static uint8_t    header[4];
static uint16_t   headerPos  = 0;
static uint16_t   payloadLen = 0;
static uint16_t   payloadPos = 0;
static uint8_t    payload[kMaxPayload];
static uint8_t    msgChannel = 0;
static bool       dirty      = false;   // pixels changed since the last show()

// -------------------------------------------------------------- LED helpers --

static void clearAll() {
  for (int i = 0; i < kLedsPerStrip * kNumStrips; i++) leds.setPixel(i, 0);
  leds.show();
}

// Copy one channel's payload onto its strip. Channels are 1-based; strip index
// is channel - 1. Anything beyond the segment's real length is ignored, and
// anything the sender omits is left as it was.
static void applyChannel(uint8_t channel, const uint8_t *data, uint16_t len) {
  if (channel < 1 || channel > kNumChannels) return;

  const uint8_t  strip = channel - 1;
  const uint16_t count = min((uint16_t)(len / 3), kChannelLen[strip]);
  const uint32_t base  = (uint32_t)strip * kLedsPerStrip;

  for (uint16_t i = 0; i < count; i++) {
    const uint8_t *px = data + i * 3;
    leds.setPixel(base + i, px[0], px[1], px[2]);
  }
  dirty = true;
}

// Channel 0 means "every channel", with the payload laid out end to end.
static void applyBroadcast(const uint8_t *data, uint16_t len) {
  uint16_t offset = 0;
  for (uint8_t ch = 1; ch <= kNumChannels && offset < len; ch++) {
    const uint16_t want = kChannelLen[ch - 1] * 3;
    const uint16_t have = min(want, (uint16_t)(len - offset));
    applyChannel(ch, data + offset, have);
    offset += want;
  }
}

// ----------------------------------------------------------------- parsing --

static void resetParser() {
  state = WAIT_HEADER;
  headerPos = payloadPos = payloadLen = 0;
}

static void consume(uint8_t b) {
  switch (state) {
    case WAIT_HEADER:
      header[headerPos++] = b;
      if (headerPos == 4) {
        msgChannel = header[0];
        const uint8_t command = header[1];
        payloadLen = ((uint16_t)header[2] << 8) | header[3];
        payloadPos = 0;

        if (command != 0) {
          // Not "set pixel colours" -- consume and ignore the body.
          state = payloadLen ? SKIP_PAYLOAD : WAIT_HEADER;
          if (!payloadLen) headerPos = 0;
        } else if (payloadLen == 0) {
          resetParser();
        } else if (payloadLen > (msgChannel == 0 ? kMaxPayload
                                                 : kMaxChannelPayload)) {
          // Longer than this message type can legitimately be: malformed. Skip
          // it rather than overflowing, and stay in sync with the stream.
          state = SKIP_PAYLOAD;
        } else {
          state = READ_PAYLOAD;
        }
      }
      break;

    case READ_PAYLOAD:
      if (payloadPos < kMaxPayload) payload[payloadPos] = b;
      payloadPos++;
      if (payloadPos >= payloadLen) {
        const uint16_t usable = min(payloadPos, kMaxPayload);
        if (msgChannel == 0) applyBroadcast(payload, usable);
        else                 applyChannel(msgChannel, payload, usable);
        resetParser();
      }
      break;

    case SKIP_PAYLOAD:
      if (++payloadPos >= payloadLen) resetParser();
      break;
  }
}

// -------------------------------------------------------------------- setup --

void setup() {
  Serial.begin(115200);

  leds.begin();
  clearAll();

  const IPAddress ip(192, 168, 1, kLastOctet);
  const IPAddress netmask(255, 255, 255, 0);
  const IPAddress gateway(192, 168, 1, 1);      // the Pi's eth0

  Ethernet.begin(ip, netmask, gateway);
  server.begin();

  Serial.printf("Funklet OPC server: board %d, %u channels, listening on ",
                BOARD, kNumChannels);
  Serial.print(ip);
  Serial.printf(":%u\r\n", kOpcPort);
}

// --------------------------------------------------------------------- loop --

void loop() {
  // One controller, one connection. If a new client arrives while we hold an
  // old socket, take the new one -- the controller reconnects after a stall and
  // the stale side may take a while to time out.
  EthernetClient incoming = server.accept();
  if (incoming) {
    if (client && client.connected()) client.stop();
    client = incoming;
    resetParser();
    Serial.println("client connected");
  }

  if (client && client.connected()) {
    int available = client.available();
    while (available-- > 0) {
      const int b = client.read();
      if (b < 0) break;
      consume((uint8_t)b);
    }

    // Latch once the socket has drained. The controller writes a whole frame
    // in one go, so this lands one show() per frame rather than one per
    // channel -- which matters, since show() holds off the next update.
    if (dirty && !client.available() && !leds.busy()) {
      leds.show();
      dirty = false;
    }
  } else if (client) {
    Serial.println("client disconnected");
    client.stop();
    resetParser();
  }
}
