// Knoc8 Desktop Agent — ESP32-C3 firmware
// Hold-to-talk button + I2S mic streaming + animated OLED face (U8g2).
// Audio is sent as framed packets: 0xAA 0x55 <len lo> <len hi> <PCM bytes>

#include <Wire.h>
#include <U8g2lib.h>
#include <ESP_I2S.h>

#define SERIAL_BAUD     921600
#define SAMPLE_RATE     16000

#define MIC_SCK_PIN     4
#define MIC_WS_PIN      5
#define MIC_SD_PIN      2

#define OLED_SDA_PIN    8
#define OLED_SCL_PIN    9
#define OLED_WIDTH      128
#define OLED_HEIGHT     64
#define OLED_ADDR       0x3C

#define BUTTON_PIN      3
#define DEBOUNCE_MS     40

#define CHUNK_SAMPLES   512

U8G2_SSD1306_128X64_NONAME_F_HW_I2C u8g2(U8G2_R0, U8X8_PIN_NONE, OLED_SCL_PIN, OLED_SDA_PIN);
I2SClass i2s;

static int32_t micRaw[CHUNK_SAMPLES];
static uint8_t frame[4 + CHUNK_SAMPLES * 2];   // header + PCM, sent in ONE write

String lineBuf;

enum FaceState { FACE_BOOT, FACE_IDLE, FACE_LISTEN, FACE_THINK, FACE_WORK, FACE_SPEAK };
FaceState face = FACE_BOOT;
char stepText[24] = "";

bool streaming = false;
bool lastRaw = HIGH;
bool buttonState = HIGH;
unsigned long lastDebounce = 0;

unsigned long lastFrame = 0;
unsigned long nextBlink = 2500;
unsigned long blinkStart = 0;
bool blinking = false;
int lookX = 0;
unsigned long nextLook = 4000;
uint8_t animPhase = 0;

// ---------------------------------------------------------------- draw helpers

void rbox(int x, int y, int w, int h, int r) {
  if (w < 1 || h < 1) return;
  int maxR = min(w, h) / 2;
  if (r > maxR) r = maxR;
  if (r < 1) u8g2.drawBox(x, y, w, h);
  else       u8g2.drawRBox(x, y, w, h, r);
}

void rframe(int x, int y, int w, int h, int r) {
  int maxR = min(w, h) / 2;
  if (r > maxR) r = maxR;
  if (r < 1) u8g2.drawFrame(x, y, w, h);
  else       u8g2.drawRFrame(x, y, w, h, r);
}

// ---------------------------------------------------------------- face

void drawEyePair(int w, int h, int y, int dx, int r) {
  int lx = 40 - w / 2 + dx;
  int rx = 88 - w / 2 + dx;
  rbox(lx, y, w, h, r);
  rbox(rx, y, w, h, r);
}

void drawHappyEyes(int y) {
  for (int e = 0; e < 2; e++) {
    int cx = (e == 0) ? 40 : 88;
    u8g2.setDrawColor(1);
    u8g2.drawDisc(cx, y + 12, 13);
    u8g2.setDrawColor(0);
    u8g2.drawDisc(cx, y + 18, 13);
    u8g2.setDrawColor(1);
  }
}

int blinkedHeight(int h) {
  if (!blinking) return h;
  unsigned long t = millis() - blinkStart;
  if (t > 240) { blinking = false; return h; }
  float p = (t < 120) ? (1.0f - t / 120.0f) : ((t - 120) / 120.0f);
  int bh = (int)(h * p);
  return bh < 2 ? 2 : bh;
}

void drawStatusLine(const char *text) {
  u8g2.setFont(u8g2_font_6x10_tr);
  int w = u8g2.getStrWidth(text);
  int x = (OLED_WIDTH - w) / 2;
  if (x < 0) x = 0;
  u8g2.drawStr(x, 63, text);
}

void drawFace() {
  u8g2.clearBuffer();
  u8g2.setDrawColor(1);
  switch (face) {
    case FACE_BOOT: {
      u8g2.setFont(u8g2_font_10x20_tr);
      int w = u8g2.getStrWidth("KNOC8");
      u8g2.drawStr((OLED_WIDTH - w) / 2, 36, "KNOC8");
      drawStatusLine("waking up...");
      break;
    }
    case FACE_IDLE: {
      int h = blinkedHeight(26);
      drawEyePair(26, h, 14 + (26 - h) / 2, lookX, 8);
      drawStatusLine("hold to talk");
      break;
    }
    case FACE_LISTEN: {
      int h = blinkedHeight(32);
      drawEyePair(30, h, 8 + (32 - h) / 2, 0, 10);
      drawStatusLine("listening...");
      break;
    }
    case FACE_THINK:
      drawEyePair(26, 10, 12, (animPhase % 12 < 6) ? -5 : 5, 4);
      for (int i = 0; i < (animPhase / 3) % 4; i++)
        u8g2.drawDisc(52 + i * 12, 47, 2);
      drawStatusLine("thinking...");
      break;
    case FACE_WORK: {
      int h = blinkedHeight(16);
      drawEyePair(26, h, 14, 0, 5);
      int pos = (animPhase * 6) % 80;
      rframe(16, 44, 96, 6, 3);
      rbox(16 + pos, 45, 16, 4, 2);
      drawStatusLine(stepText[0] ? stepText : "working...");
      break;
    }
    case FACE_SPEAK: {
      int bounce = (animPhase % 4 < 2) ? 0 : 2;
      drawHappyEyes(8 + bounce);
      drawStatusLine("speaking...");
      break;
    }
  }
  u8g2.sendBuffer();
}

void updateFace() {
  unsigned long now = millis();
  if (now - lastFrame < 80) return;
  lastFrame = now;
  animPhase++;
  if ((face == FACE_IDLE || face == FACE_LISTEN || face == FACE_WORK)
      && !blinking && now >= nextBlink) {
    blinking = true; blinkStart = now; nextBlink = now + 2000 + random(3500);
  }
  if (face == FACE_IDLE && now >= nextLook) {
    int r = random(3);
    lookX = (r == 0) ? -7 : (r == 1) ? 7 : 0;
    nextLook = now + 1500 + random(3000);
  }
  if (face != FACE_IDLE) lookX = 0;
  drawFace();
}

void setFace(FaceState f) {
  if (face != f) {
    face = f;
    animPhase = 0;
    if (f != FACE_WORK) stepText[0] = '\0';
    drawFace();
  }
}

// ---------------------------------------------------------------- mic

void setupMic() {
  i2s.setPins(MIC_SCK_PIN, MIC_WS_PIN, -1, MIC_SD_PIN, -1);
  i2s.begin(I2S_MODE_STD, SAMPLE_RATE, I2S_DATA_BIT_WIDTH_32BIT,
            I2S_SLOT_MODE_MONO, I2S_STD_SLOT_LEFT);
}

void serviceMic() {
  if (!streaming) return;
  size_t bytesRead = i2s.readBytes((char *)micRaw, sizeof(micRaw));
  int samples = bytesRead / sizeof(int32_t);
  if (samples <= 0) return;

  int16_t *pcm = (int16_t *)(frame + 4);
  for (int i = 0; i < samples; i++) {
    int32_t s = micRaw[i] >> 14;
    if (s > 32767) s = 32767;
    if (s < -32768) s = -32768;
    pcm[i] = (int16_t)s;
  }
  uint16_t nBytes = samples * 2;
  frame[0] = 0xAA;
  frame[1] = 0x55;
  frame[2] = nBytes & 0xFF;
  frame[3] = nBytes >> 8;
  Serial.write(frame, 4 + nBytes);      // one write = one intact frame
}

void flushMic() {
  for (int i = 0; i < 4 && i2s.available() > 0; i++) {
    i2s.readBytes((char *)micRaw, sizeof(micRaw));
  }
}

// ---------------------------------------------------------------- button

void pollButton() {
  bool raw = digitalRead(BUTTON_PIN);
  unsigned long now = millis();

  if (raw != lastRaw) {
    lastRaw = raw;
    lastDebounce = now;
    return;
  }
  if (now - lastDebounce < DEBOUNCE_MS) return;
  if (raw == buttonState) return;

  buttonState = raw;
  if (raw == LOW) {
    flushMic();
    streaming = true;
    Serial.print("\nBUTTON:DOWN\n");
    setFace(FACE_LISTEN);
  } else {
    streaming = false;
    Serial.print("\nBUTTON:UP\n");      // leading \n guarantees a clean line start
  }
}

// ---------------------------------------------------------------- serial

void handleLine(const String &line) {
  if (line.startsWith("STATUS:")) {
    String s = line.substring(7);
    if (s == "IDLE")           { streaming = false; setFace(FACE_IDLE); }
    else if (s == "LISTENING") setFace(FACE_LISTEN);
    else if (s == "THINKING")  { streaming = false; setFace(FACE_THINK); }
    else if (s == "EXECUTING") setFace(FACE_WORK);
    else if (s == "SPEAKING")  setFace(FACE_SPEAK);
  } else if (line.startsWith("STEP:")) {
    String s = line.substring(5);
    s.trim();
    strncpy(stepText, s.c_str(), sizeof(stepText) - 1);
    stepText[sizeof(stepText) - 1] = '\0';
  } else if (line.startsWith("REC:STOP")) {
    streaming = false;
  }
}

void pollSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      lineBuf.trim();
      if (lineBuf.length()) handleLine(lineBuf);
      lineBuf = "";
    } else if (lineBuf.length() < 128) {
      lineBuf += c;
    }
  }
}

// ---------------------------------------------------------------- main

void setup() {
  Serial.setTxBufferSize(4096);   // MUST be before begin(); default 256 truncates chunks
  Serial.begin(SERIAL_BAUD);
  Serial.setTxTimeoutMs(20);      // wait briefly instead of dropping bytes

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  lastRaw = digitalRead(BUTTON_PIN);
  buttonState = lastRaw;

  Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
  u8g2.setI2CAddress(OLED_ADDR << 1);
  u8g2.setBusClock(400000);
  u8g2.begin();
  drawFace();

  setupMic();

  Serial.print("\nREADY\n");
  setFace(FACE_IDLE);
}

void loop() {
  pollSerial();
  pollButton();
  serviceMic();
  updateFace();
}