/*
 * light weight WS2812 lib include
 *
 * Version 2.3  - Nev 29th 2015
 * Author: Tim (cpldcpu@gmail.com)
 *
 * Please do not change this file! All configuration is handled in "ws2812_config.h"
 *
 * License: GNU GPL v2+ (see License.txt)
 +
 */

#ifndef LIGHT_WS2812_H_
#define LIGHT_WS2812_H_

#include <avr/io.h>
#include <avr/interrupt.h>


#define WS2812_PORT B
#define WS2812_PIN 1

#if !defined(CONCAT)
#define CONCAT(a, b) a##b
#endif

#if !defined(CONCAT_EXP)
#define CONCAT_EXP(a, b) CONCAT(a, b)
#endif

#define WS2812_PORT_REG CONCAT_EXP(PORT, WS2812_PORT)
#define WS2812_DDR_REG CONCAT_EXP(DDR, WS2812_PORT)
#define WS2812_PIN_MASK _BV(WS2812_PIN)

///////////////////////////////////////////////////////////////////////
// Define Reset time in µs.
//
// This is the time the library spends waiting after writing the data.
//
// WS2813 needs 300 µs reset time
// WS2812 and clones only need 50 µs
//
///////////////////////////////////////////////////////////////////////
#define WS2812_RESETTIME 100

#define MAX_NUM_LEDS 255

/*
*  Structure of the LED array
*/
struct cRGB
{
    uint8_t g;
    uint8_t r;
    uint8_t b;
};

void ws2812_send_bytes(const uint16_t count, const uint8_t *array);
void ws2812_send_pixels(const uint16_t count, const struct cRGB *array);
void ws2812_send_uid(uint8_t uid);
void ws2812_clear(void);

#endif /* LIGHT_WS2812_H_ */