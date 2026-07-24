#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
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

#define CHUNK_SAMPLES   512

Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
I2SClass i2s;

static int32_t micRaw[CHUNK_SAMPLES];
static int16_t pcm[CHUNK_SAMPLES];

String lineBuf;

enum FaceState { FACE_BOOT, FACE_IDLE, FACE_LISTEN, FACE_THINK, FACE_WORK, FACE_SPEAK };
FaceState face = FACE_BOOT;
char stepText[24] = "";

unsigned long lastFrame = 0;
unsigned long nextBlink = 2500;
unsigned long blinkStart = 0;
bool blinking = false;
int lookX = 0;
unsigned long nextLook = 4000;
uint8_t animPhase = 0;

void drawEyePair(int w, int h, int y, int dx, int r) {
  int lx = 40 - w / 2 + dx;
  int rx = 88 - w / 2 + dx;
  display.fillRoundRect(lx, y, w, h, r, SSD1306_WHITE);
  display.fillRoundRect(rx, y, w, h, r, SSD1306_WHITE);
}

void drawHappyEyes(int y) {
  for (int e = 0; e < 2; e++) {
    int cx = (e == 0) ? 40 : 88;
    display.fillCircle(cx, y + 12, 13, SSD1306_WHITE);
    display.fillCircle(cx, y + 18, 13, SSD1306_BLACK);
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
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  int len = strlen(text);
  int x = (OLED_WIDTH - len * 6) / 2;
  if (x < 0) x = 0;
  display.setCursor(x, 55);
  display.print(text);
}

void drawFace() {
  display.clearDisplay();
  switch (face) {
    case FACE_BOOT:
      display.setTextSize(2); display.setTextColor(SSD1306_WHITE);
      display.setCursor(28, 20); display.print("KNOC8");
      drawStatusLine("waking up...");
      break;
    case FACE_IDLE: {
      int h = blinkedHeight(26);
      drawEyePair(26, h, 14 + (26 - h) / 2, lookX, 8);
      drawStatusLine("say  hey agent");
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
        display.fillCircle(52 + i * 12, 47, 2, SSD1306_WHITE);
      drawStatusLine("thinking...");
      break;
    case FACE_WORK: {
      int h = blinkedHeight(16);
      drawEyePair(26, h, 14, 0, 5);
      int pos = (animPhase * 6) % 96;
      display.drawRoundRect(16, 44, 96, 6, 3, SSD1306_WHITE);
      display.fillRoundRect(16 + pos, 45, 16, 4, 2, SSD1306_WHITE);
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
  display.display();
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

void setupMic() {
  i2s.setPins(MIC_SCK_PIN, MIC_WS_PIN, -1, MIC_SD_PIN, -1);
  i2s.begin(I2S_MODE_STD, SAMPLE_RATE, I2S_DATA_BIT_WIDTH_32BIT,
            I2S_SLOT_MODE_MONO, I2S_STD_SLOT_LEFT);
}

void streamMicChunk() {
  size_t bytesRead = i2s.readBytes((char *)micRaw, sizeof(micRaw));
  int samples = bytesRead / sizeof(int32_t);
  if (samples <= 0) return;
  for (int i = 0; i < samples; i++) {
    int32_t s = micRaw[i] >> 14;
    if (s > 32767) s = 32767;
    if (s < -32768) s = -32768;
    pcm[i] = (int16_t)s;
  }
  int nBytes = samples * sizeof(int16_t);
  Serial.printf("CHUNK:%d\n", nBytes);
  Serial.write((uint8_t *)pcm, nBytes);
}

void setFace(FaceState f) {
  if (face != f) {
    face = f;
    animPhase = 0;
    if (f != FACE_WORK) stepText[0] = '\0';
  }
}

void handleLine(const String &line) {
  if (line.startsWith("STATUS:")) {
    String s = line.substring(7);
    if (s == "IDLE")           setFace(FACE_IDLE);
    else if (s == "LISTENING") setFace(FACE_LISTEN);
    else if (s == "THINKING")  setFace(FACE_THINK);
    else if (s == "EXECUTING") setFace(FACE_WORK);
    else if (s == "SPEAKING")  setFace(FACE_SPEAK);
  } else if (line.startsWith("STEP:")) {
    String s = line.substring(5);
    s.trim();
    strncpy(stepText, s.c_str(), sizeof(stepText) - 1);
    stepText[sizeof(stepText) - 1] = '\0';
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

void setup() {
  Serial.begin(SERIAL_BAUD);

  Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
  Wire.setClock(400000);
  display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  drawFace();

  setupMic();

  Serial.print("READY\n");
  setFace(FACE_IDLE);
}

void loop() {
  pollSerial();
  streamMicChunk();
  updateFace();
}
