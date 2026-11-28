#include <WiFi.h>
#include <HTTPClient.h>
#include <WebSocketsClient.h>   // Install "WebSockets" by Markus Sattler via Library Manager
#include <driver/i2s.h>

// ==============================================================
// 1. NETWORK & DUAL-BACKEND CONFIGURATION
// ==============================================================
const char* WIFI_SSID     = "YOUR_WIFI_NAME";     // Put your Wi-Fi name
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"; // Put your Wi-Fi password

// LOCAL BACKEND (When running uvicorn on your PC)
// Detected from your machine: 10.27.28.40 (or your LAN IPv4)
const char* LOCAL_HOST    = "10.27.28.40";
const int   LOCAL_PORT    = 8000;

// CLOUD BACKEND (Render Production URL)
// https://echo-xsr5.onrender.com/ -> wss://echo-xsr5.onrender.com/ws/audio
const char* CLOUD_HOST    = "echo-xsr5.onrender.com";
const int   CLOUD_PORT    = 443; // Secure WSS port

const char* TARGET_LANG   = "hi"; // Target language: 'hi', 'es', 'fr', 'de', etc.
const char* DEVICE_ID     = "ESP32_001";

WebSocketsClient webSocket;
bool isUsingCloud = false;

// ==============================================================
// 2. I2S PIN ASSIGNMENTS
// ==============================================================
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

// Audio parameters: 16-bit signed PCM @ 16kHz mono
#define SAMPLE_RATE       16000
#define CHUNK_SIZE        1024  // 1024 bytes = 512 samples (~32ms chunks)

// ==============================================================
// 3. I2S HARDWARE INITIALIZATION
// ==============================================================
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

// ==============================================================
// 4. WEBSOCKET EVENT HANDLER
// ==============================================================
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_CONNECTED:
      Serial.printf("[WS] CONNECTED to %s backend!\n", isUsingCloud ? "RENDER CLOUD" : "LOCAL PC");
      break;

    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected from server. Retrying...");
      break;

    case WStype_TEXT:
      // Frame 1: Server sends JSON containing transcription and translation
      Serial.printf("\n[Translation Result]:\n%s\n", payload);
      break;

    case WStype_BIN:
      // Frame 2: Server sends synthesized WAV audio bytes
      Serial.printf("[Audio In]: Received %u bytes of translated audio. Playing...\n", length);
      // Skip the 44-byte standard WAV header to feed pure PCM into I2S DAC
      if (length > 44) {
        size_t bytes_written = 0;
        i2s_write(I2S_SPK_PORT, (char*)(payload + 44), length - 44, &bytes_written, portMAX_DELAY);
      }
      break;

    case WStype_ERROR:
      Serial.println("[WS] WebSocket Error encountered.");
      break;
  }
}

// ==============================================================
// 5. AUTO-DETECT ACTIVE BACKEND (LOCAL vs CLOUD)
// ==============================================================
bool checkLocalBackend() {
  HTTPClient http;
  String localHealthUrl = "http://" + String(LOCAL_HOST) + ":" + String(LOCAL_PORT) + "/health";
  
  Serial.print("Probing Localhost Backend: ");
  Serial.println(localHealthUrl);

  http.begin(localHealthUrl);
  http.setTimeout(1500); // 1.5 seconds timeout
  int httpCode = http.GET();
  http.end();

  if (httpCode == 200) {
    Serial.println(">>> Localhost Backend detected and ONLINE! <<<");
    return true;
  } else {
    Serial.printf(">>> Localhost Backend offline or unreachable (HTTP Code: %d) <<<\n", httpCode);
    return false;
  }
}

// ==============================================================
// 6. SETUP & MAIN LOOP
// ==============================================================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n==============================================");
  Serial.println("  Echo ESP32-S3 Voice Translation Terminal    ");
  Serial.println("==============================================");

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
  Serial.println("\n[Wi-Fi] Connected! ESP32 IP: " + WiFi.localIP().toString());

  // WebSocket URI query string
  String wsUrl = "/ws/audio?device_id=" + String(DEVICE_ID) + "&target_language=" + String(TARGET_LANG);

  // AUTO-DETECT: Check if Localhost server is active
  if (checkLocalBackend()) {
    // 1. CONNECT TO LOCALHOST (ws://LOCAL_HOST:8000/ws/audio...)
    isUsingCloud = false;
    Serial.printf("[Mode] Connecting to LOCALHOST: ws://%s:%d%s\n", LOCAL_HOST, LOCAL_PORT, wsUrl.c_str());
    webSocket.begin(LOCAL_HOST, LOCAL_PORT, wsUrl.c_str());
  } else {
    // 2. FALLBACK TO RENDER CLOUD (wss://echo-xsr5.onrender.com/ws/audio...)
    isUsingCloud = true;
    Serial.printf("[Mode] Connecting to RENDER CLOUD: wss://%s:443%s\n", CLOUD_HOST, wsUrl.c_str());
    webSocket.beginSSL(CLOUD_HOST, CLOUD_PORT, wsUrl.c_str());
  }

  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(3000);
}

void loop() {
  webSocket.loop();

  // When connected, continuously read from INMP441 microphone and stream PCM to backend
  if (webSocket.isConnected()) {
    uint8_t audio_buffer[CHUNK_SIZE];
    size_t bytes_read = 0;

    // Read raw 16kHz PCM from INMP441
    esp_err_t result = i2s_read(I2S_MIC_PORT, (char*)audio_buffer, CHUNK_SIZE, &bytes_read, (10 / portTICK_PERIOD_MS));
    if (result == ESP_OK && bytes_read > 0) {
      // Send binary audio frame
      webSocket.sendBIN(audio_buffer, bytes_read);
    }
  }
}
