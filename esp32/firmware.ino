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

void showStatus(const String &line1, const String &line2 = "") {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("  KNOC8 AGENT");
  display.drawLine(0, 10, OLED_WIDTH, 10, SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(0, 22);
  display.println(line1);
  display.setTextSize(1);
  display.setCursor(0, 48);
  display.println(line2);
  display.display();
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

void handleLine(const String &line) {
  if (line.startsWith("STATUS:")) {
    String s = line.substring(7);
    if (s == "IDLE")           showStatus("IDLE", "Say 'Hey Agent'");
    else if (s == "LISTENING") showStatus("LISTEN", "Speak now...");
    else if (s == "THINKING")  showStatus("THINK", "Processing...");
    else if (s == "EXECUTING") showStatus("WORKING", "Running task...");
    else if (s == "SPEAKING")  showStatus("SPEAK", "Say wake word to stop");
    else                       showStatus(s, "");
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
  display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  showStatus("BOOT", "Starting...");

  setupMic();

  Serial.print("READY\n");
  showStatus("IDLE", "Say 'Hey Agent'");
}

void loop() {
  pollSerial();
  streamMicChunk();
}
