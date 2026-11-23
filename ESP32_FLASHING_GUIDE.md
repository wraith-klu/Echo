# 🔌 ESP32-S3 Hardware Flashing & Connection Guide

This guide walks you through wiring and flashing your **ESP32-S3** with the [`echo_esp32.ino`](file:///p:/CapsTron%20Project%20-%201/echo_esp32.ino) firmware to establish real-time bi-directional speech translation with your Echo backend.

---

## 📌 1. Hardware Pinout & Wiring

Connect the **INMP441 I2S Microphone** and **MAX98357A I2S Class-D DAC/Speaker** to the ESP32-S3 as shown below:

```
┌─────────────────────────────────┐           ┌─────────────────────────────────┐
│     INMP441 Microphone (Input)  │           │   MAX98357A Speaker (Output)    │
├───────────────┬─────────────────┤           ├───────────────┬─────────────────┤
│ INMP441 Pin   │ ESP32-S3 Pin    │           │ MAX98357A Pin │ ESP32-S3 Pin    │
├───────────────┼─────────────────┤           ├───────────────┼─────────────────┤
│ VDD           │ 3.3V (⚠️ Not 5V)│           │ VIN           │ 5V (or 3.3V)    │
│ GND           │ GND             │           │ GND           │ GND             │
│ SD (Data)     │ GPIO 4          │           │ DIN (Data)    │ GPIO 7          │
│ WS (Word/LR)  │ GPIO 5          │           │ LRC (Word)    │ GPIO 8          │
│ SCK (Clock)   │ GPIO 6          │           │ BCLK (Clock)  │ GPIO 9          │
│ L/R           │ GND (Left)      │           │ GAIN / SD     │ GND / Unused    │
└───────────────┴─────────────────┘           └───────────────┴─────────────────┘
```

> ⚠️ **Important Voltage Warning**: The INMP441 operates strictly on **3.3V**. Connecting VDD to 5V will permanently damage the MEMS sensor.

---

## 🛠️ 2. Arduino IDE Setup (One-Time)

### Step 2.1: Install ESP32 Board Core
1. Open **Arduino IDE**.
2. Go to **File ➔ Preferences**.
3. Under **Additional boards manager URLs**, add:
   ```text
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Click **OK**.
5. Go to **Tools ➔ Board ➔ Boards Manager...**, search for `esp32` by **Espressif Systems**, and click **Install**.

### Step 2.2: Install Required WebSocket Library
1. In Arduino IDE, go to **Tools ➔ Manage Libraries...** (or press `Ctrl + Shift + I`).
2. Search for:
   ```text
   WebSockets
   ```
3. Locate **WebSockets** authored by **Markus Sattler**.
4. Click **Install**.

---

## ⚙️ 3. Configure Firmware Settings

Open the [`echo_esp32.ino`](file:///p:/CapsTron%20Project%20-%201/echo_esp32.ino) file located in your project root:

Edit lines 8–18 with your Wi-Fi credentials and local PC IP address:

```cpp
// 1. Enter your Wi-Fi Network credentials
const char* WIFI_SSID     = "Your_WiFi_Name";
const char* WIFI_PASSWORD = "Your_WiFi_Password";

// 2. Set your computer's local IP address running FastAPI
const char* BACKEND_HOST  = "192.168.1.XX"; // Replace with your PC's IPv4
const int   BACKEND_PORT  = 8000;

// 3. Set desired target output language ('es', 'fr', 'de', 'hi', 'zh', etc.)
const char* TARGET_LANG   = "hi";
const char* DEVICE_ID     = "ESP32_001";
```

### 🔍 How to find your PC's IP address:
On Windows, open PowerShell / Terminal and run:
```powershell
ipconfig
```
Look for **IPv4 Address** under your active Wi-Fi or Ethernet adapter (e.g. `192.168.1.15`).

---

## ⚡ 4. Board Selection & Flashing

1. Connect your ESP32-S3 board to your PC via a **USB Data Cable** (make sure the cable supports data, not power-only).
2. In Arduino IDE, configure the **Tools** menu:
   - **Board**: `ESP32S3 Dev Module`
   - **Upload Speed**: `921600`
   - **USB CDC On Boot**: `Enabled`
   - **Flash Size**: `4MB` (or `8MB` / `16MB` based on your board)
   - **Port**: Select the COM port assigned to your ESP32 (e.g. `COM3`, `COM5`).

3. **Upload Firmware**:
   - Hold down the **BOOT** button on the ESP32 board.
   - Click the **Upload** arrow button (or `Ctrl + U`).
   - As soon as the terminal shows `Connecting...___...___...`, release the **BOOT** button.
   - Wait until it shows `Hard resetting via RTS pin...` (Flash Complete).

---

## 🚀 5. Testing & Verification

1. Open the Arduino **Serial Monitor** (**Tools ➔ Serial Monitor** or `Ctrl + Shift + M`).
2. Set the baud rate to **`115200 baud`**.
3. Press the **EN (Reset)** button on the ESP32.
4. You should see the following startup logs:
   ```text
   Connecting to Wi-Fi: Your_WiFi_Name
   ....
   Wi-Fi Connected! IP: 192.168.1.42
   [WS] Connected to Echo Backend!
   ```
5. **Speak into the INMP441 Microphone**:
   - The ESP32 streams raw PCM chunks over WebSockets.
   - The backend VAD detects end of speech, triggers ASR ➔ MT ➔ TTS.
   - The Serial Monitor will print:
     ```text
     [Translation JSON]: {"transcription":"Hello world","translation":"नमस्ते दुनिया","latencies":{...}}
     [Audio In]: Playing 32768 bytes of translated speech...
     ```
   - The translated voice will play back through the MAX98357A speaker!
