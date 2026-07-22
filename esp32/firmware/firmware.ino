#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <driver/i2s.h>

#define SERIAL_BAUD     921600
#define SAMPLE_RATE     16000

#define MIC_SCK_PIN     14
#define MIC_WS_PIN      15
#define MIC_SD_PIN      32

#define OLED_WIDTH      128
#define OLED_HEIGHT     64
#define OLED_ADDR       0x3C

#define CHUNK_SAMPLES   512

Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);

static int32_t micRaw[CHUNK_SAMPLES];
static int16_t pcm[CHUNK_SAMPLES];

String lineBuf;
bool micEnabled = true;

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
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 256,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num = MIC_SCK_PIN,
    .ws_io_num = MIC_WS_PIN,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = MIC_SD_PIN
  };
  i2s_driver_install(I2S_NUM_0, &cfg, 0, NULL);
  i2s_set_pin(I2S_NUM_0, &pins);
}

void streamMicChunk() {
  size_t bytesRead = 0;
  i2s_read(I2S_NUM_0, micRaw, sizeof(micRaw), &bytesRead, pdMS_TO_TICKS(100));
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
    if (s == "IDLE") {
      micEnabled = true;
      showStatus("IDLE", "Say 'Hey Agent'");
    } else if (s == "LISTENING") {
      micEnabled = true;
      showStatus("LISTEN", "Speak now...");
    } else if (s == "THINKING") {
      micEnabled = false;
      showStatus("THINK", "Processing...");
    } else if (s == "EXECUTING") {
      micEnabled = false;
      showStatus("WORKING", "Running task...");
    } else if (s == "SPEAKING") {
      micEnabled = false;
      showStatus("SPEAK", "");
    } else {
      showStatus(s, "");
    }
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
  Serial.setRxBufferSize(4096);

  Wire.begin();
  display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR);
  showStatus("BOOT", "Starting...");

  setupMic();

  Serial.print("READY\n");
  showStatus("IDLE", "Say 'Hey Agent'");
}

void loop() {
  pollSerial();
  if (micEnabled) {
    streamMicChunk();
  }
}
