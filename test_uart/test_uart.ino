
#include <TXOnlySerial.h>
#include "usi_serial.h"

#define VERBOSE 0
#define DEBUG_SERIAL 1
#define RX_PIN 0
#define TX_DEBUG_PIN 2

#define TEST_BAUDRATE 200000
#define TEST_BYTE 86

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

// The index of the byte currently being received
uint16_t byte_index = 0;

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

void setup()
{
    // IO directions
    pinMode(RX_PIN, INPUT);

    // Setup Serial output for debug
    debug_serial.begin(9600);
    debug_serial.println("");
    debug_serial.println("Funky serial tester");
    
    // Setup the input serial port
    InitSerial(BaudsToPrescaler(TEST_BAUDRATE));
    interrupts();
    debug_serial.print("Current serial input baudrate: ");
    debug_serial.print(TEST_BAUDRATE);
    debug_serial.println(" Baud");
    noInterrupts();
}

void loop()
{
    // Wait for messages
    uint8_t c = GetSerialByte(false);
    if (c != TEST_BYTE) {
        PORTB = 0x14;
        PORTB = 0x04;
        SquareB1();
        debug_serial.print("Got bad byte: ");
        debug_serial.print(c, HEX);
        debug_serial.println("");
        FlushSerial();
    }
}

#if 0

/////////////////////////////////////////////////////
// All the following functions implement the serial interface.
// they should be included in a library of their own
//////////////////////////////////////////////////////


uint32_t PrescalerToBauds(uint8_t prescaler)
{
    return 16000000 / (static_cast<uint32_t>(prescaler));
}

uint32_t BaudsToPrescaler(uint32_t baud)
{
    return 16000000 / baud;
}

// Configure TIMER0 and the Universal Serial Interface (USI) for a specific baudrate
// The actual baudrate will be given by the formula:
//   baudrate = 16Mhz / (8 * prescaler)
// Speeds up to 400Kb (prescaler = 5) were tested
void InitSerial(uint8_t prescaler)
{
    // Timer 0 configuration
    GTCCR = 1 << TSM; // Stop the timer while we are configuring
    OCR0A = prescaler - 1;
    OCR0B = 1;
    TCCR0A = (3 << WGM00);  // Fast PWM mode
    TCCR0B = (1 << WGM02) | // Fast PWM mode
             (1 << CS00);   // Use clock input directly (no prescaler)

    // USI configuration register
    USICR = 0 << USISIE | // No start detection interrupt (used for I2C)
            0 << USIOIE | // Overflow interrupt disable
            0 << USIWM0 | // No fancy SPI or I2C mode
            1 << USICS0 | // Use Timer 0 as clock
            0 << USICLK;  // No clock strobe
    USISR = 0;            // Clear all interrupts and counter

    // Precompute the halfbit delay. This will be used to delay the start
    //  of the USI sampling by half a bit. The constant is used to compensate
    //  for code delay
    halfbit_delay = (prescaler >> 1) + 10;

    interrupts();
    debug_serial.print("Current serial input prescaler: ");
    debug_serial.println(prescaler);
    debug_serial.print("Current serial input baudrate: ");
    debug_serial.print(PrescalerToBauds(prescaler));
    debug_serial.println(" Baud");
    noInterrupts();
}

inline void WaitForStartBit() {
    // Wait for a start bit
    while(PINB & 1);

    // We can now start the timer and USI
    TCNT0 = halfbit_delay; // Set the counter to half the prescaler.
                          // This will implement a half bit delay
    USISR = 1 << USIOIF | // Clear interrupt flag
            7;            // Set counter to 7
                          // (will overflow at 16, after 9 samples)
    GTCCR = 1 << TSM;    // Start the timer
    ToggleB1();
}

inline void FlushSerial()
{
    // Turn off the timer
    GTCCR = 0 << TSM;
}

// Reverse the order of bits. AVRs don't have barrel shifters, so shifts are
// not eficient. It has however a pretty nice check bit and branch operation,
// and this ends up being really fast.
inline uint8_t ReverseBits(uint8_t in)
{
    uint8_t out = 0;
    if (in & 0x01) out |= 0x80;
    if (in & 0x02) out |= 0x40;
    if (in & 0x04) out |= 0x20;
    if (in & 0x08) out |= 0x10;
    if (in & 0x10) out |= 0x08;
    if (in & 0x20) out |= 0x04;
    if (in & 0x40) out |= 0x02;
    if (in & 0x80) out |= 0x01;
    return out; 
}

inline uint8_t GetSerialByte(bool last_byte)
{
    // If the timer is on, the USI is already busy capturing a byte, we just
    //  need to wait until it's done. Otherwise we wait for a start bit
    if (!(GTCCR & (1 << TSM))) {
        WaitForStartBit();
    }

    // Wait for the USI to complete its sampling
    while (! (USISR & (1 << USIOIF)));
    GTCCR = 0 << TSM;     // Stop the timer
    uint8_t data = USIBR;
    ToggleB1();

    // Wait until the line goes back to high (when we see the stop bit)
    while(!(PINB & 1));

    // If it is the last byte, we don't need to wait for the next start bit
    if (!last_byte) {
        WaitForStartBit();
    }

    return ReverseBits(data);
}
#endif
