// NOTE:
//  The ATTINY85 does not use a crystal and per datasheet, its internal oscillator's
//  frequency can vary +/-10%. In practice the bound is much closer, but we should implement
//  a routine which regularly tunes the clock frequency by looking at the position of the serial
//  stream bit transitions.

#include <FAB_LED.h>
#include <TXOnlySerial.h>
#include <CRC.h>
#include <EEPROM.h>
#include "usi_serial.h"

#define VERBOSE 0
#define DEBUG_SERIAL 0
#define LEDS_PIN 1
#define RX_PIN 0
#define TX_DEBUG_PIN 2

#define MAX_NUM_LEDS 230

#define MAGIC_BYTE 0x55
#define CRC_POLYNOMIAL 0x07

#define BROADCAST_UID 0

#define INITIAL_SERIAL_BAUDRATE 200000

#define UID_UNDEFINED 0xFF

// Internal array of LED data
ws2812b<B, LEDS_PIN> fab_led;
const grb grb_white[1] = {{255, 255, 255}};
const grb grb_black[1] = {{0, 0, 0}};
const grb grb_red[1] = {{0, 255, 0}};
const grb grb_green[1] = {{255, 0, 0}};
const grb grb_blue[1] = {{0, 0, 255}};

#if DEBUG_SERIAL
TXOnlySerial debug_serial(TX_DEBUG_PIN);
#else
// Dummy serial port class
class DummySerial {
 public:
  inline void begin(int baudrate) {};
  size_t print(const char[]) { return 0; };
  size_t print(int, int = DEC) { return 0; };
  size_t print(unsigned int, int = DEC) { return 0; };
  size_t print(unsigned long, int = DEC) { return 0; };

  size_t println(const char[]) { return 0; };
  size_t println(int, int = DEC) { return 0; };
  size_t println(unsigned int, int = DEC) { return 0; };
  size_t println(unsigned long, int = DEC) { return 0; };
  size_t println(void) { return 0; };
} debug_serial;
#endif

// The UID for this board. The bar will only answer to messages sent to this specific UID,
//  or to the broadcast UID
// Fixed for now. Should be written in Flash for each board.
uint8_t uid = 1;

// The actual number of LEDs. The initial value is 8 to display the uid before LED messages arrive.
uint8_t num_leds = 8;
uint8_t new_num_leds = 8;

// The index of the byte currently being received
uint16_t byte_index = 0;
// The current state of the deserializer
enum
{
    IDLE,
    UID,
    CMD,
    NUM_LEDS,
    DATA_LEDS,
    PRESCALER,
    CRC
} state = IDLE;

//
// Messages formats
//
typedef enum
{
    CMD_LEDS = 1,
    CMD_SERIAL_BAUDRATE = 2,
    CMD_BOOTLOADER = 3,
} Cmd;
Cmd cmd;

// Message: Set serial baudrate
// The baudrate is given as a clock prescaler value. See definition of InitSerial() for details.
struct __attribute__((packed)) SpeedMsg
{
    uint8_t magic;
    uint8_t uid;
    Cmd cmd = CMD_SERIAL_BAUDRATE;
    uint8_t prescaler;
    uint8_t crc;
};
uint8_t prescaler;

// Message: Set Leds
typedef uint16_t LedColor;
struct __attribute__((packed)) LedMsg
{
    uint8_t magic;
    uint8_t uid;
    Cmd cmd = CMD_LEDS;
    uint16_t num_leds;
    LedColor leds[MAX_NUM_LEDS];
    uint8_t crc;
};
LedColor led_colors[MAX_NUM_LEDS];
uint8_t *led_colors_bytes = reinterpret_cast<uint8_t *>(led_colors);

// R5G6B5 version of sendPixels
void sendPixelsR5G6B5(
    const uint16_t count,
    uint16_t * pixelArray)
{
  uint8_t bytes[3];

  for (uint16_t i = 0; i < count; i++) 
  {
    const uint16_t elem = pixelArray[i];
    bytes[0] = (elem >> 3) & 0xFC;
    bytes[1] = (elem >> 8) & 0xF8;
    bytes[2] = (elem << 3) & 0xF8;
    fab_led.sendBytes(3, bytes);
  }
}

void sendPixelsSolidColor(const uint16_t numPixels, const grb * color)
{
  for( uint16_t i = 0; i < numPixels; i++) 
  {
    fab_led.sendBytes(3, (const uint8_t *) color);
  }
}

// Helper function to print a value in binary WITH leading zeros.
void PrintBinary(uint8_t data, bool line_feed)
{
    for (int i = 0; i < 8; i++)
    {
        debug_serial.print(data >> 7, BIN);
        data <<= 1;
    }
    if (line_feed)
    {
        debug_serial.println("");
    }
}

void startBootloader()
{
  // jump LOADER
  asm volatile
  (
  
      // 'FLASH' message into stack
      "  ldi   r30, 0x42                           \n\t" // 'B'
      "  push  r30                                 \n\t"
      "  ldi   r30, 0x4F                           \n\t" // 'O'
      "  push  r30                                 \n\t"
      "  ldi   r30, 0x4F                           \n\t" // 'O'
      "  push  r30                                 \n\t"
      "  ldi   r30, 0x54                           \n\t" // 'T'
      "  push  r30                                 \n\t"
  
      // jump into bootloader (0x1C00)
      "  ldi   r30, 0x00                           \n\t"
      "  ldi   r31, 0x0E                           \n\t"
      "  ijmp                                      \n\t"
  );
}

void setup()
{
    // Read UID from EEPROM. If the UID was never set this value will be UID_UNDEFINED.
    uid = EEPROM.read(0);
    
    // IO directions
    pinMode(RX_PIN, INPUT);

    // Setup the LED strip
    if (uid == UID_UNDEFINED) 
    {
      sendPixelsSolidColor(MAX_NUM_LEDS, grb_red);
    }
    else 
    {
      sendPixelsSolidColor(MAX_NUM_LEDS, grb_black);
    }

    // Setup Serial output for debug
    debug_serial.begin(9600);
    debug_serial.println("");
    debug_serial.println("Funky LEDs");
    debug_serial.print("Number of LEDs: ");
    debug_serial.println(num_leds);
    debug_serial.print("UID: ");
    if (uid == UID_UNDEFINED) 
    {
      debug_serial.println("undefined");
    } 
    else
    {
      debug_serial.println(uid);
    }
    
    // Setup the input serial port
    InitSerial(BaudsToPrescaler(INITIAL_SERIAL_BAUDRATE));

    noInterrupts();
}

void loop()
{

    // Wait for messages
    uint8_t c = GetSerialByte(state == CRC);
    switch (state)
    {
    case IDLE:
        if (c == MAGIC_BYTE)
        {
            state = UID;
        }
        else
        {
            if (VERBOSE)
            {
                interrupts();
                debug_serial.print("Bad Magic: 0x");
                debug_serial.println(c, HEX);
                noInterrupts();
            }
        }
        break;
    case UID:
        if (c == uid || c == BROADCAST_UID)
        {
            state = CMD;
            byte_index = 0;
        }
        else
        {
            if (VERBOSE)
            {
                interrupts();
                debug_serial.print("Bad UID: ");
                debug_serial.println(c);
                noInterrupts();
            }
            FlushSerial();
            state = IDLE;
        }
        break;
    case CMD:
        cmd = static_cast<Cmd>(c);
        switch (c)
        {
        case CMD_LEDS:
            state = NUM_LEDS;
            break;
        case CMD_SERIAL_BAUDRATE:
            state = PRESCALER;
            break;
        case CMD_BOOTLOADER:
            startBootloader();
            break;
        default:
            if (VERBOSE)
            {
                interrupts();
                debug_serial.print("Bad command: 0x");
                debug_serial.println(c, HEX);
                noInterrupts();
            }
            state = IDLE;
            FlushSerial();
            break;
        }
        break;
    case NUM_LEDS:
        new_num_leds = c;
        if (new_num_leds > MAX_NUM_LEDS)
        {
          // Ignore commands that have too many LEDs
          state = IDLE;
          FlushSerial();
        }
        else
        {
          state = DATA_LEDS;
          byte_index = 0;
        }
        break;
    case DATA_LEDS:
        led_colors_bytes[byte_index++] = c;
        if (byte_index == new_num_leds * 2)
        {
            state = CRC;
        }
        break;
    case PRESCALER:
        prescaler = c;
        state = CRC;
        break;
    case CRC:
        state = IDLE;
        // compute what the CRC should be
        uint8_t crc = 0;
        switch (cmd)
        {
        case CMD_LEDS:
            crc = crc8(led_colors_bytes, new_num_leds * 2, CRC_POLYNOMIAL);
            break;
        case CMD_SERIAL_BAUDRATE:
            crc = crc8(&prescaler, 1, CRC_POLYNOMIAL);
            break;
        default:
            break;
        }
        if (c == crc)
        {
            switch (cmd)
            {
            case CMD_LEDS:
                if (new_num_leds != num_leds)
                {
                    // Update FastLED in case the number of LEDs has changed.
                    interrupts();
                    debug_serial.print("Updating # of LEDs: ");
                    debug_serial.print(num_leds);
                    debug_serial.print(" -> ");
                    debug_serial.println(new_num_leds);
                    noInterrupts();
                    num_leds = new_num_leds;
                }
                sendPixelsR5G6B5(num_leds, led_colors);
                break;
            case CMD_SERIAL_BAUDRATE:
                InitSerial(prescaler);
                break;
            default:
                break;
            }
        }
        else
        {
            if (VERBOSE)
            {
                interrupts();
                debug_serial.print("Bad CRC: 0x");
                debug_serial.println(c, HEX);
                noInterrupts();
            }
        }
        break;
    }
}
