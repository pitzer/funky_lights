#include <FastLED.h>

#define PIN_LEDS 2

#define NUM_SEGMENTS 14
const int num_leds[NUM_SEGMENTS] = {66, 61, 57, 53, 49, 45, 41, 37, 34, 30, 29, 27, 25, 24};
#define NUM_LEDS_TOTAL 578

CRGB leds[NUM_LEDS_TOTAL];
static const CRGBPalette16 palette = ForestColors_p;


void setup() {
  // Setup the LED strips
  FastLED.addLeds<WS2812B, PIN_LEDS, BRG>(leds, NUM_LEDS_TOTAL);
  FastLED.setBrightness(180);
}

void loop() {
  int32_t t = millis();
  CRGB* segment_addr = leds;
  FastLED.clear();
  for (int segment = 0; segment < NUM_SEGMENTS - 1; segment++) {
    // Color each segment with the right color
    int32_t palette_index = (segment * 255 / NUM_SEGMENTS) + t / 30;    
    CRGB segment_color = ColorFromPalette(palette, palette_index, 255, LINEARBLEND);
    for (int i = 0; i < num_leds[segment]; i++) {
      *(segment_addr + i) = segment_color;
    }
    // Add two red dots at the right angles
    int32_t angle_deg = (t / 4 + segment * 10) % 360;
    int32_t index1 = ( angle_deg * num_leds[segment] / 360 ) % num_leds[segment];
    int32_t index2 = ((600 - angle_deg) * num_leds[segment] / 360 ) % num_leds[segment];
    *(segment_addr + index1) = CRGB::Black;
    *(segment_addr + index2) = CRGB::Black;
    // increment the segment address
    segment_addr += num_leds[segment];
  }
  for (int i = 0; i < num_leds[NUM_SEGMENTS - 1]; i++) {
    *(segment_addr + i) = CRGB::CRGB(0xFF0040);
  }
  FastLED.show();
}
