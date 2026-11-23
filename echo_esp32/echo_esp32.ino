#include <WiFi.h>
#include <WebSocketsClient.h>   // Install "WebSockets" by Markus Sattler via Library Manager
#include <driver/i2s.h>

// ============================
// 1. NETWORK & BACKEND CONFIG
// ============================
const char* WIFI_SSID     = "Wraaiiitthhh";
const char* WIFI_PASSWORD = "Wraaiiitthhh";

// If testing locally, use your Laptop/PC's LAN IP (e.g. 192.168.1.15)
// If deployed in cloud, use domain without "http" / "ws" (e.g. "api.yourdomain.com")
const char* BACKEND_HOST  = "192.168.1.15";
const int   BACKEND_PORT  = 8000;
const char* TARGET_LANG   = "hi"; // e.g., 'es', 'fr', 'de', 'hi'
const char* DEVICE_ID     = "ESP32_001";

WebSocketsClient webSocket;

// ============================
// 2. I2S PIN ASSIGNMENTS
// ============================
// INMP441 Microphone (I2S Port 0 - Input)
#define I2S_MIC_PORT      I2S_NUM_0
#define I2S_MIC_SCK       6
#define I2S_MIC_WS        5
#define I2S_MIC_SD        4

// MAX98357A Speaker (I2S Port 1 - Output)
#define I2S_SPK_PORT      I2S_NUM_1
#define I2S_SPK_BCLK      9
#define I2S_SPK_LRC       8
#define I2S_SPK_DIN       7

// Audio config: 16-bit signed PCM @ 16kHz mono
#define SAMPLE_RATE       16000
#define CHUNK_SIZE        1024  // 1024 bytes = 512 samples (~32ms chunks)

// ============================
// 3. I2S DRIVER SETUP
// ============================
void init_i2s_mic() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 256,
    .use_apll = false
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_MIC_SCK,
    .ws_io_num = I2S_MIC_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_MIC_SD
  };

  i2s_driver_install(I2S_MIC_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_MIC_PORT, &pin_config);
}

void init_i2s_speaker() {
  i2s_config_t i2s_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 256,
    .use_apll = false
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_SPK_BCLK,
    .ws_io_num = I2S_SPK_LRC,
    .data_out_num = I2S_SPK_DIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };

  i2s_driver_install(I2S_SPK_PORT, &i2s_config, 0, NULL);
  i2s_set_pin(I2S_SPK_PORT, &pin_config);
}

// ============================
// 4. WEBSOCKET EVENT HANDLER
// ============================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_CONNECTED:
      Serial.println("[WS] Connected to Echo Backend!");
      break;

    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected from server. Reconnecting...");
      break;

    case WStype_TEXT:
      // Frame 1: Server sends JSON with transcription and translation
      Serial.printf("[Translation JSON]: %s\n", payload);
      break;

    case WStype_BIN:
      // Frame 2: Server sends synthesized WAV audio bytes
      Serial.printf("[Audio In]: Playing %u bytes of translated speech...\n", length);
      // Skip the 44-byte WAV header to feed pure PCM to I2S
      if (length > 44) {
        size_t bytes_written = 0;
        i2s_write(I2S_SPK_PORT, (char*)(payload + 44), length - 44, &bytes_written, portMAX_DELAY);
      }
      break;

    case WStype_ERROR:
      Serial.println("[WS] Error encountered.");
      break;
  }
}

// ============================
// 5. SETUP & MAIN LOOP
// ============================
void setup() {
  Serial.begin(115200);
  delay(1000);

  // Initialize Audio Hardware
  init_i2s_mic();
  init_i2s_speaker();

  // Connect to Wi-Fi
  Serial.printf("Connecting to Wi-Fi: %s\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWi-Fi Connected! IP: " + WiFi.localIP().toString());

  // Build the WebSocket URI: /ws/audio?device_id=ESP32_001&target_language=hi
  String wsUrl = "/ws/audio?device_id=" + String(DEVICE_ID) + "&target_language=" + String(TARGET_LANG);

  // Initialize WebSocket Client
  // Note: For HTTPS/WSS (Port 443), use webSocket.beginSSL(BACKEND_HOST, 443, wsUrl.c_str());
  webSocket.begin(BACKEND_HOST, BACKEND_PORT, wsUrl.c_str());
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(3000);
}

void loop() {
  webSocket.loop();

  // If connected, read audio from mic and stream to backend
  if (webSocket.isConnected()) {
    uint8_t audio_buffer[CHUNK_SIZE];
    size_t bytes_read = 0;

    // Read raw 16kHz PCM from INMP441
    esp_err_t result = i2s_read(I2S_MIC_PORT, (char*)audio_buffer, CHUNK_SIZE, &bytes_read, (10 / portTICK_PERIOD_MS));
    if (result == ESP_OK && bytes_read > 0) {
      // Send binary frame
      webSocket.sendBIN(audio_buffer, bytes_read);
    }
  }
}
