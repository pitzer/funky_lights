#include <FastLED.h>

#define PIN_LEDS 2

#define NUM_LEDS_TOTAL 128

CRGB leds[NUM_LEDS_TOTAL];
static const CRGBPalette16 palette = RainbowStripeColors_p;


void setup() {
  // Setup the LED strips
  FastLED.addLeds<WS2812B, PIN_LEDS, BRG>(leds, NUM_LEDS_TOTAL);
  FastLED.setBrightness(200);
}

void loop() {
  int32_t t = millis() / 10;
  for (int i = 0; i < NUM_LEDS_TOTAL; i++) {
    leds[i] = ColorFromPalette(palette, (i * 255 / NUM_LEDS_TOTAL + t) % 255, 255, LINEARBLEND);
  }
  FastLED.show();
}
