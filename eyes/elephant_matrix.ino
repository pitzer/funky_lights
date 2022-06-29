#include "FastLED.h"

// Data pin that led data will be written out over
#define DATA_PIN 2

#define MATRIX_WIDTH   11
#define MATRIX_HEIGHT  11
#define NUM_LEDS_RIGHT 97
#define NUM_LEDS_LEFT  91

#define NUM_LEDS      (NUM_LEDS_RIGHT + NUM_LEDS_LEFT)
CRGBArray<NUM_LEDS>   leds;

enum Side {LEFT, RIGHT};
                    
const int8_t kMappingRight[] = {
  -1,  -1,  -1,   4,   3,   2,   1,   0,  -1,  -1,  -1,  
  -1,  -1,   5,   6,   7,   8,   9,  10,  11,  -1,  -1,
  -1,  20,  19,  18,  17,  16,  15,  14,  13,  12,  -1,
  21,  22,  23,  24,  25,  26,  27,  28,  29,  30,  31,
  42,  41,  40,  39,  38,  37,  36,  35,  34,  33,  32,
  43,  44,  45,  46,  47,  48,  49,  50,  51,  52,  53,
  64,  63,  62,  61,  60,  59,  58,  57,  56,  55,  54,
  65,  66,  67,  68,  69,  70,  71,  72,  73,  74,  75,
  -1,  84,  83,  82,  81,  80,  79,  78,  77,  76,  -1,
  -1,  -1,  85,  86,  87,  88,  89,  90,  91,  -1,  -1,
  -1,  -1,  -1,  96,  95,  94,  93,  92,  -1,  -1,  -1
};

const int8_t kMappingLeft[] = {
  -1,  -1,  -1,  59,  58,  37,  36,   9,  -1,  -1,  -1, 
  -1,  -1,  78,  60,  57,  38,  35,   8,  10,  -1,  -1,
  -1,  79,  77,  61,  56,  39,  34,   7,  11,   0,  -1,
  90,  80,  76,  62,  55,  40,  33,   6,  12,   1,  -1,
  89,  81,  75,  63,  54,  41,  32,   5,  13,   2,  -1,
  88,  82,  74,  64,  53,  42,  31,   4,  14,  -1,  -1,
  87,  83,  73,  65,  52,  43,  30,   3,  15,  21,  -1,
  86,  84,  72,  66,  51,  44,  29,  22,  16,  20,  -1,
  -1,  85,  71,  67,  50,  45,  28,  23,  17,  19,  -1,
  -1,  -1,  70,  68,  49,  46,  27,  24,  18,  -1,  -1,
  -1,  -1,  -1,  69,  48,  47,  26,  25,  -1,  -1,  -1
};

// This function sets up the ledsand tells the controller about them
void setup() {
  delay(1000);
  FastLED.addLeds<WS2811, DATA_PIN, RGB>(leds, NUM_LEDS);
  //FastLED.setBrightness(20);
}

int index(Side side, uint8_t x, uint8_t y)
{
  int i;
  int index;
  if (x < 0 || x >= MATRIX_WIDTH) return -1;
  if (y < 0 || y >= MATRIX_HEIGHT) return -1;
  i = (y * MATRIX_WIDTH) + x;
  if (side == Side::LEFT) {
    index = kMappingLeft[i];
  } else {
    index = kMappingRight[i];
  }
  if (index > 0 && side == Side::LEFT) index += NUM_LEDS_RIGHT;
  return index;
}

void setColor(Side side, uint8_t x, uint8_t y, CRGB color)
{
  int i = index(side, x, y);
  if (i < 0) return;
  leds[i] = color;
}

CRGB getColor(Side side, uint8_t x, uint8_t y)
{
  int i = index(side, x, y);
  if (i < 0) return CRGB::Black;
  return leds[i];
}

void drawLine(Side side, int16_t x0, int16_t y0, int16_t x1, int16_t y1, CRGB Col)
{
  int16_t dx = x1 - x0;
  int16_t dy = y1 - y0;
  if (abs(dx) >= abs(dy))
  {
    int32_t y = ((int32_t)y0 << 16) + 32768;
    // Support a single dot line without diving by 0 and crashing below
    if (!dx) {
      setColor(side, x0, (y >> 16), Col);
    } else {
      int32_t f = ((int32_t)dy << 16) / (int32_t)abs(dx);
      if (dx >= 0)
      {
        for (; x0<=x1; ++x0,y+=f)
          setColor(side, x0, (y >> 16), Col);
      }
      else
      {
        for (; x0>=x1; --x0,y+=f)
          setColor(side, x0, (y >> 16), Col);
      }
    }
  }
  else
  {
    int32_t f = ((int32_t)dx << 16) / (int32_t)abs(dy);
    int32_t x = ((int32_t)x0 << 16) + 32768;
    if (dy >= 0)
    {
      for (; y0<=y1; ++y0,x+=f)
        setColor(side, (x >> 16), y0, Col);
    }
    else
    {
      for (; y0>=y1; --y0,x+=f)
        setColor(side, (x >> 16), y0, Col);
    }
  }
}


void drawLine(int16_t x0, int16_t y0, int16_t x1, int16_t y1, CRGB Col) {
  drawLine(Side::RIGHT, x0, y0, x1, y1, Col);
  drawLine(Side::LEFT, x0, y0, x1, y1, Col);
}

void horizontalMirror(Side side, bool FullHeight=true)
{
  int ty, y, x, xx;

  if (FullHeight)
    ty = MATRIX_HEIGHT - 1;
  else
    ty = (MATRIX_HEIGHT / 2);
  for (y=ty; y>=0; --y)
  {
    for (x=(MATRIX_WIDTH/2)-1,xx=((MATRIX_WIDTH+1)/2); x>=0; --x,++xx) {
      CRGB color = getColor(side, x, y);
      setColor(side, xx, y, color);
    }
  }
}

void horizontalMirror(bool FullHeight=true)
{
  horizontalMirror(Side::RIGHT, FullHeight);
  horizontalMirror(Side::LEFT, FullHeight);
}

void verticalMirror(Side side)
{
  int y, yy, x;

  for (y=(MATRIX_HEIGHT/2)-1,yy=((MATRIX_HEIGHT+1)/2); y>=0; --y,++yy)
  {
    for (x=MATRIX_WIDTH-1; x>=0; --x) {
      CRGB color = getColor(side, x, y);
      setColor(side, x, yy, color);
    }
  }
}

void verticalMirror() {
  verticalMirror(Side::RIGHT);
  verticalMirror(Side::LEFT);
}

void drawFilledRectangle(Side side, int16_t x0, int16_t y0, int16_t x1, int16_t y1, CRGB Col)
{
  int16_t y = min(y0, y1);
  for (int16_t c=abs(y1-y0); c>=0; --c,++y)
    drawLine(side, x0, y, x1, y, Col);
}

void drawFilledRectangle(int16_t x0, int16_t y0, int16_t x1, int16_t y1, CRGB Col)
{
  drawFilledRectangle(Side::RIGHT, x0, y0, x1, y1, Col);
  drawFilledRectangle(Side::LEFT, x0, y0, x1, y1, Col);
}

void drawFilledCircle(Side side, int16_t xc, int16_t yc, uint16_t r, CRGB Col)
{
  int16_t x = r;
  int16_t y = 0;
  int16_t e = 1 - x;
  while (x >= y)
  {
    drawLine(side, xc + x, yc + y, xc - x, yc + y, Col);
    drawLine(side, xc + y, yc + x, xc - y, yc + x, Col);
    drawLine(side, xc - x, yc - y, xc + x, yc - y, Col);
    drawLine(side, xc - y, yc - x, xc + y, yc - x, Col);
    ++y;
    if (e >= 0)
    {
      --x;
      e += 2 * ((y - x) + 1);
    }
    else
      e += (2 * y) + 1;
  }
}

void drawFilledCircle(int16_t xc, int16_t yc, uint16_t r, CRGB Col) {
  drawFilledCircle(Side::RIGHT, xc, yc, r, Col);
  drawFilledCircle(Side::LEFT, xc, yc, r, Col);
}

void drawEye(int16_t xc, int16_t yc) {
  FastLED.setBrightness(100);
  drawFilledRectangle(0, 0, MATRIX_WIDTH, MATRIX_HEIGHT, CRGB::White);
  drawFilledCircle(xc, yc, 3, CRGB::Black);
}

uint8_t hue;
int16_t counter = 0;

void loop()
{
  int16_t sx, sy, x, y;
  uint8_t h;

  FastLED.clear();
  FastLED.setBrightness(255);

  h = hue;
  if (counter < 1125)
  {
    // ** Fill LED's with diagonal stripes
    for (x=0; x<(MATRIX_WIDTH+MATRIX_HEIGHT); ++x)
    {
      drawLine(x - MATRIX_HEIGHT, MATRIX_HEIGHT - 1, x, 0, CHSV(h, 255, 255));
      h+=16;
    }
  }
  else if (counter < 2250)
  {
    // ** Fill LED's with horizontal stripes
    for (y=0; y<MATRIX_HEIGHT; ++y)
    {
      drawLine(0, y, MATRIX_WIDTH - 1, y, CHSV(h, 255, 255));
      h+=16;
    }
  }
  hue+=4;

  if (counter < 125)
    ;
  else if (counter < 375) {
    horizontalMirror();
  }
  else if (counter < 625) {
    verticalMirror();
  }
  else if (counter < 2250)
   ;
//  else if (counter < 1500)
//    leds.TriangleTopMirror();
//  else if (counter < 1750)
//    leds.TriangleBottomMirror();
//  else if (counter < 2000)
//    leds.QuadrantTopTriangleMirror();
//  else if (counter < 2250)
//    leds.QuadrantBottomTriangleMirror();
  else if (counter < 2300) drawEye(5, 7);
  else if (counter < 2305) drawEye(5, 8);
  else if (counter < 2310) drawEye(5, 9);
  else if (counter < 2315) drawEye(5, 9);
  else if (counter < 2320) drawEye(5, 9);
  else if (counter < 2600) drawEye(5, 9);
  else if (counter < 2605) drawEye(6, 9);
  else if (counter < 2610) drawEye(7, 9);
  else if (counter < 2615) drawEye(8, 9);
  else if (counter < 2620) drawEye(9, 9);
  else if (counter < 2625) drawEye(9, 9);  
  else if (counter < 2900) drawEye(9, 9); 
  else if (counter < 2905) drawEye(8, 9);
  else if (counter < 2910) drawEye(7, 9);
  else if (counter < 2900) drawEye(6, 9);
  else if (counter < 3200) drawEye(6, 9);
  else if (counter < 3205) drawEye(6, 8);
  else if (counter < 3200) drawEye(6, 7);
  else if (counter < 3200) drawEye(6, 6);
  else if (counter < 3500) drawEye(6, 6);
  else if (counter < 3505) drawEye(5, 5);
  else if (counter < 3510) drawEye(4, 4);
  else if (counter < 3515) drawEye(3, 4);
  else if (counter < 3900) drawEye(3, 4);
  else if (counter < 3905) drawEye(3, 5);
  else if (counter < 3910) drawEye(3, 6);
  else if (counter < 3915) drawEye(3, 7);
  else if (counter < 3920) drawEye(3, 8);
  else if (counter < 4500) drawEye(3, 8);
  else if (counter < 4505) drawEye(4, 7);
  else if (counter < 4510) drawEye(5, 6);
  else if (counter < 4515) drawEye(6, 6);
  else if (counter < 5000) drawEye(6, 6);
  
  counter++;
  if (counter >= 5000)
    counter = 0;
  FastLED.show();
}

//// This function runs over and over, and is where you do the magic to light
//// your leds.
//void loop() {
//  // Move a single white led 
//  for(uint8_t y = 0; y < MATRIX_HEIGHT; y++) {   
//    for(uint8_t x = 0; x < MATRIX_WIDTH; x++) {   
//      // Turn our current led on to white, then show the leds
//      setColor(Side::LEFT, x, y, CRGB::White);
//      setColor(Side::RIGHT, x, y, CRGB::White);
//      
//      // Show the leds (only one of which is set to white, from above)
//      FastLED.show();
//
//      // Wait a little bit
//      delay(50);
//
//      // Turn our current led back to black for the next loop around
//      setColor(Side::LEFT, x, y, CRGB::Black);
//      setColor(Side::RIGHT, x, y, CRGB::Black);
//    }
//  }
//}
