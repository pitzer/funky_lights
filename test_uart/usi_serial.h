// Very fast receive only UART based on the ATTiny85 Universal Serial Interface.

// All these functions should be included in their own library !!!!

uint8_t halfbit_delay;

// Toggle pin 6 (I/O B1) very quickly. This can be used to get a timing reference on an oscilloscope
// This assumes that the state of the other IOs is know (B0 = 0, B1 = 0, B2 = 1, B3 = 0)
inline void ToggleB1()
{
    PORTB = 0x06;
    PORTB = 0x04;
}

// Keep pin 6 (I/O B1) high for 10us. This can be used to trigger a scope
// This assumes that the state of the other IOs is know (B0 = 0, B1 = 0, B2 = 1,
// B3 = 0)
inline void SquareB1()
{
    PORTB = 0x06;
    delayMicroseconds(10);
    PORTB = 0x04;
}

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

