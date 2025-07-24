#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <time.h>
#include <EEPROM.h>
#include <ArduinoJson.h>

// Default credentials - CHANGE THESE
const char* default_ssid = "YOUR_WIFI_SSID";
const char* default_password = "YOUR_WIFI_PASSWORD";
const char* default_ap_ssid = "Health monitor V1";
const char* default_ap_password = "YOUR_AP_PASSWORD";

// Supabase settings - CHANGE THESE
const char* supabaseUrl = "YOUR_SUPABASE_URL";
const char* supabaseTableFollowHour = "followhour";
const char* supabaseTableOneTest = "onetest";
const char* supabaseKey = "YOUR_SUPABASE_ANON_KEY";

// Firmware version
const char* FIRMWARE_VERSION = "1.0.0";

// NTP Settings
const char* ntpServer = "pool.ntp.org";
const long gmtOffset_sec = 25200; // GMT+7 for Vietnam
const int daylightOffset_sec = 0;

// EEPROM Settings
#define EEPROM_SIZE 128
#define SSID_ADDR 0
#define PASS_ADDR 32
#define VALID_FLAG_ADDR 64
#define AP_SSID_ADDR 65
#define AP_PASS_ADDR 96
#define OFFLINE_MODE_ADDR 127
#define VALID_FLAG 0xAA

// Wi-Fi timeout
#define WIFI_TIMEOUT 30000
#define RECONNECT_INTERVAL 30000
#define MAX_RECONNECT_ATTEMPTS 3

// Serial2 pins for sensor
#define RX_PIN 16
#define TX_PIN 17

// Buzzer pin
#define BUZZER_PIN 5

// Web server
WebServer server(80);

// Buffers
char stored_ssid[32];
char stored_password[32];
char stored_ap_ssid[32];
char stored_ap_password[32];
bool offline_mode = false;
unsigned long lastReconnectAttempt = 0;
int reconnectAttempts = 0;

// Sensor variables
unsigned long previousFollowHourMillis = 0;
const long followHourInterval = 15000;
unsigned long fingerStartMillis = 0;
bool fingerDetected = false;
bool oneTestSent = false;

// Function prototypes
void readEEPROMString(int addr, char* buffer, size_t maxLen);
void writeEEPROMString(int addr, const char* data, size_t maxLen);
void clearEEPROM();
bool isValidApPassword(const String& password);
bool isValidSsid(const String& ssid);
bool isValidSensorData(float bpm, float temp);
void printLocalTime();
void startAPMode();
void startWebServer();
void handleRoot();
void handleWiFi();
void handleScan();
void handleStatus();
void handleClear();
void sendToSupabase(const char* table, float bpm, float temp, const char* timestampField);
String getCurrentTimestamp();
void playBuzzer(int times);

// HTML for the web interface
const char* html = R"rawliteral(
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Health Monitor Wi-Fi Configuration</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {
      font-family: sans-serif;
      background: linear-gradient(135deg, #1e3a8a, #1e40af);
      color: #111;
      margin: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
    }
    .card {
      background: #fff;
      padding: 2rem;
      border-radius: 1rem;
      box-shadow: 0 10px 20px rgba(0,0,0,0.2);
      max-width: 400px;
      width: 100%;
    }
    h1 {
      text-align: center;
      font-size: 1.5rem;
      margin-bottom: 1rem;
    }
    .form-toggle {
      display: flex;
      justify-content: center;
      gap: 1rem;
      margin-bottom: 1rem;
    }
    .btn {
      padding: 0.5rem 1rem;
      font-weight: bold;
      border-radius: 5px;
      border: none;
      cursor: pointer;
    }
    .btn-blue {
      background: #2563eb;
      color: #fff;
    }
    .btn-gray {
      background: #4b5563;
      color: #fff;
    }
    .btn-red {
      background: #dc2626;
      color: #fff;
      margin-top: 1rem;
      width: 100%;
    }
    form {
      display: none;
    }
    form.active {
      display: block;
    }
    label {
      display: block;
      font-size: 0.9rem;
      margin-bottom: 0.2rem;
    }
    input[type="text"], input[type="password"] {
      box-sizing: border-box;
      padding: 0.5rem;
      height: 2.5rem;
      font-size: 1rem;
      border: 1px solid #ccc;
      border-radius: 5px;
      width: 100%;
    }
    .custom-dropdown {
      position: relative;
      width: 100%;
      border: 1px solid #ccc;
      border-radius: 5px;
      background: white;
    }
    .dropdown-selected {
      padding: 0.5rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .dropdown-selected::after {
      content: url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20fill='gray'%20viewBox='0%200%2024%2024'%20xmlns='http://www.w3.org/2000/svg'%3E%3Cpath%20d='M7%2010l5%205%205-5z'/%3E%3C/svg%3E");
      width: 1rem;
    }
    .dropdown-menu {
      position: absolute;
      top: 100%;
      left: 0;
      right: 0;
      background: white;
      border: 1px solid #ccc;
      border-radius: 5px;
      max-height: 200px;
      overflow-y: auto;
      display: none;
      z-index: 10;
    }
    .dropdown-menu.active {
      display: block;
    }
    .dropdown-item {
      padding: 0.5rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .dropdown-item:hover {
      background: #f0f0f0;
    }
    .signal-bar {
      width: 100px;
      height: 10px;
      background: #e0e0e0;
      border-radius: 5px;
      overflow: hidden;
      margin-left: 10px;
    }
    .signal-bar-fill {
      height: 100%;
      background: #2563eb;
      transition: width 0.3s;
    }
    .password-toggle {
      float: right;
      font-size: 1rem;
      cursor: pointer;
      color: #2563eb;
    }
    .submit {
      background: #2563eb;
      color: white;
      padding: 0.75rem;
      width: 100%;
      border: none;
      border-radius: 5px;
      font-weight: bold;
      margin-top: 1rem;
    }
    #status {
      text-align: center;
      font-size: 0.9rem;
      margin-top: 1rem;
    }
    .refresh {
      font-size: 0.85rem;
      color: #2563eb;
      text-align: right;
      cursor: pointer;
      display: block;
      margin-top: 0.3rem;
      margin-bottom: 0.8rem;
    }
    .offline-toggle {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-top: 1rem;
    }
    .switch {
      position: relative;
      display: inline-block;
      width: 40px;
      height: 20px;
    }
    .switch input {
      opacity: 0;
      width: 0;
      height: 0;
    }
    .slider {
      position: absolute;
      cursor: pointer;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: #ccc;
      transition: 0.4s;
      border-radius: 20px;
    }
    .slider:before {
      position: absolute;
      content: "";
      height: 16px;
      width: 16px;
      left: 2px;
      bottom: 2px;
      background-color: white;
      transition: 0.4s;
      border-radius: 50%;
    }
    input:checked + .slider {
      background-color: #2563eb;
    }
    input:checked + .slider:before {
      transform: translateX(20px);
    }
    .error {
      color: red;
      font-size: 0.8rem;
      margin-top: 0.2rem;
    }
    footer {
      text-align: center;
      font-size: 0.8rem;
      color: #666;
      margin-top: 1rem;
    }
  </style>
</head>
<body>
  <div class="card">
    <h1>Configuration</h1>
    <div class="form-toggle">
      <button onclick="showForm('wifi')" class="btn btn-blue">Wi-Fi</button>
      <button onclick="showForm('ap')" class="btn btn-gray">Access Point</button>
    </div>

    <form id="wifi-form" class="active">
      <label for="ssid">Wi-Fi SSID</label>
      <div class="custom-dropdown">
        <div class="dropdown-selected" id="dropdown-selected">Select a network</div>
        <div class="dropdown-menu" id="dropdown-menu"></div>
      </div>
      <input type="hidden" id="ssid" name="ssid">
      <div id="ssid_error" class="error"></div>
      <div class="refresh" onclick="scanNetworks()">↻ Refresh Networks</div>

      <label for="password">Wi-Fi Password 
        <span class="password-toggle" onclick="togglePassword('password')">🔓</span>
      </label>
      <input type="password" id="password" />

      <button type="button" onclick="submitWiFi()" class="submit">Save Wi-Fi</button>
    </form>

    <form id="ap-form">
      <label for="ap_ssid">AP SSID</label>
      <input type="text" id="ap_ssid" />
      <div id="ap_ssid_error" class="error"></div>

      <label for="ap_password">AP Password 
        <span class="password-toggle" onclick="togglePassword('ap_password')">🔓</span>
      </label>
      <input type="password" id="ap_password" />
      <div id="ap_password_error" class="error"></div>

      <button type="button" onclick="submitAP()" class="submit">Save AP</button>
    </form>

    <div class="offline-toggle">
      <label for="offline_mode">Offline Mode</label>
      <label class="switch">
        <input type="checkbox" id="offline_mode" onchange="toggleOfflineMode()">
        <span class="slider"></span>
      </label>
    </div>

    <button type="button" onclick="clearCredentials()" class="btn btn-red">Clear Credentials</button>

    <div id="status"></div>
    <footer>Firmware Version: 1.0.0</footer>
  </div>

<script>
function showForm(type) {
  document.getElementById('wifi-form').classList.remove('active');
  document.getElementById('ap-form').classList.remove('active');
  if (type === 'wifi') {
    document.getElementById('wifi-form').classList.add('active');
    scanNetworks();
  } else {
    document.getElementById('ap-form').classList.add('active');
  }
  document.getElementById('status').textContent = '';
  document.getElementById('ssid_error').textContent = '';
  document.getElementById('ap_ssid_error').textContent = '';
  document.getElementById('ap_password_error').textContent = '';
}

function togglePassword(id) {
  const input = document.getElementById(id);
  input.type = input.type === 'password' ? 'text' : 'password';
}

function calculateSignalWidth(rssi) {
  if (rssi <= -90) return 10;
  if (rssi >= -30) return 90;
  return 10 + (rssi + 90) * (80 / 60);
}

async function scanNetworks() {
  const dropdownSelected = document.getElementById('dropdown-selected');
  const dropdownMenu = document.getElementById('dropdown-menu');
  const ssidInput = document.getElementById('ssid');
  dropdownSelected.textContent = 'Scanning...';
  dropdownMenu.innerHTML = '';
  try {
    const res = await fetch('/scan');
    const list = await res.json();
    dropdownMenu.innerHTML = '';
    if (list.length === 0) {
      dropdownSelected.textContent = 'No networks found';
      return;
    }
    list.forEach(network => {
      const item = document.createElement('div');
      item.className = 'dropdown-item';
      item.innerHTML = `
        <span>${network.ssid}</span>
        <div class="signal-bar">
          <div class="signal-bar-fill" style="width: ${calculateSignalWidth(network.rssi)}%"></div>
        </div>
      `;
      item.onclick = () => {
        dropdownSelected.textContent = network.ssid;
        ssidInput.value = network.ssid;
        dropdownMenu.classList.remove('active');
      };
      dropdownMenu.appendChild(item);
    });
    dropdownSelected.textContent = 'Select a network';
    ssidInput.value = '';
  } catch (e) {
    dropdownSelected.textContent = 'Error scanning';
    dropdownMenu.innerHTML = '<div class="dropdown-item">Error scanning</div>';
  }
}

function toggleDropdown() {
  const dropdownMenu = document.getElementById('dropdown-menu');
  dropdownMenu.classList.toggle('active');
}

async function postData(data) {
  const status = document.getElementById('status');
  try {
    status.style.color = '#111';
    status.textContent = 'Sending...';
    const response = await fetch('/wifi', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (response.ok) {
      status.style.color = 'green';
      status.textContent = 'Saved. Restarting in 3s...';
      setTimeout(() => location.reload(), 3000);
    } else {
      const errorText = await response.text();
      throw new Error(errorText || 'Save failed');
    }
  } catch (e) {
    status.style.color = 'red';
    status.textContent = 'Error: ' + e.message;
  }
}

function validateSsid(ssid) {
  if (ssid.length === 0) {
    return "SSID cannot be empty";
  }
  if (ssid.length > 32) {
    return "SSID cannot exceed 32 characters";
  }
  return "";
}

function validateApPassword(password) {
  if (password.length < 8) {
    return "Password must be at least 8 characters long";
  }
  if (password.length > 31) {
    return "Password cannot exceed 31 characters";
  }
  return "";
}

function submitWiFi() {
  const ssid = document.getElementById('ssid').value;
  const password = document.getElementById('password').value;
  const errorDiv = document.getElementById('ssid_error');
  
  if (!ssid || !password) {
    errorDiv.textContent = 'Please enter SSID and password';
    return;
  }
  
  const ssidError = validateSsid(ssid);
  if (ssidError) {
    errorDiv.textContent = ssidError;
    return;
  }
  
  errorDiv.textContent = '';
  postData({ ssid, password });
}

function submitAP() {
  const ap_ssid = document.getElementById('ap_ssid').value;
  const ap_password = document.getElementById('ap_password').value;
  const ssidErrorDiv = document.getElementById('ap_ssid_error');
  const passErrorDiv = document.getElementById('ap_password_error');
  
  if (!ap_ssid || !ap_password) {
    ssidErrorDiv.textContent = 'Please enter AP SSID and password';
    return;
  }
  
  const ssidError = validateSsid(ap_ssid);
  if (ssidError) {
    ssidErrorDiv.textContent = ssidError;
    return;
  }
  
  const passwordError = validateApPassword(ap_password);
  if (passwordError) {
    passErrorDiv.textContent = passwordError;
    return;
  }
  
  ssidErrorDiv.textContent = '';
  passErrorDiv.textContent = '';
  postData({ ap_ssid, ap_password });
}

async function toggleOfflineMode() {
  const offlineMode = document.getElementById('offline_mode').checked;
  postData({ offline_mode: offlineMode });
}

async function clearCredentials() {
  const status = document.getElementById('status');
  status.style.color = '#111';
  status.textContent = 'Clearing credentials...';
  try {
    const response = await fetch('/clear', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}'
    });
    if (response.ok) {
      status.style.color = 'green';
      status.textContent = 'Credentials cleared. Restarting in 3s...';
      setTimeout(() => location.reload(), 3000);
    } else {
      throw new Error('Clear failed');
    }
  } catch (e) {
    status.style.color = 'red';
    status.textContent = 'Error: ' + e.message;
  }
}

document.getElementById('dropdown-selected').onclick = toggleDropdown;
scanNetworks();

async function loadOfflineMode() {
  try {
    const res = await fetch('/status');
    const data = await res.json();
    document.getElementById('offline_mode').checked = data.offline_mode;
  } catch (e) {
    console.error('Error fetching offline mode:', e);
  }
}
loadOfflineMode();
</script>
</body>
</html>
)rawliteral";

void readEEPROMString(int addr, char* buffer, size_t maxLen) {
  for (size_t i = 0; i < maxLen; i++) {
    char c = EEPROM.read(addr + i);
    if (c == 0 || c == 0xFF) {
      buffer[i] = 0;
      break;
    }
    buffer[i] = c;
  }
  buffer[maxLen - 1] = 0;
}

void writeEEPROMString(int addr, const char* data, size_t maxLen) {
  for (size_t i = 0; i < maxLen; i++) {
    EEPROM.write(addr + i, data[i]);
    if (data[i] == 0) break;
  }
}

void clearEEPROM() {
  for (int i = 0; i < EEPROM_SIZE; i++) {
    EEPROM.write(i, 0xFF);
  }
  EEPROM.commit();
  Serial.println("EEPROM cleared. Restarting...");
  delay(1000);
  ESP.restart();
}

bool isValidApPassword(const String& password) {
  return password.length() >= 8 && password.length() <= 31;
}

bool isValidSsid(const String& ssid) {
  if (ssid.length() == 0) {
    return false;
  }
  if (ssid.length() > 32) {
    return false;
  }
  for (size_t i = 0; i < ssid.length(); i++) {
    if (ssid[i] < 32) {
      return false;
    }
  }
  return true;
}

bool isValidSensorData(float bpm, float temp) {
  return bpm >= 30 && bpm <= 200 && temp >= 20 && temp <= 45;
}

void printLocalTime() {
  struct tm timeinfo;
  if (!getLocalTime(&timeinfo)) {
    Serial.println("Failed to get time");
    return;
  }
  char timeString[20];
  strftime(timeString, sizeof(timeString), "%S:%M:%H - %d:%m:%Y", &timeinfo);
  Serial.println(timeString);
}

void playBuzzer(int times) {
  for (int i = 0; i < times; i++) {
    tone(BUZZER_PIN, 1000, 200); // 1000 Hz for 200 ms
    delay(300); // Short pause between beeps
  }
}

void setup() {
  Serial.begin(9600);
  Serial2.begin(115200, SERIAL_8N1, RX_PIN, TX_PIN);
  EEPROM.begin(EEPROM_SIZE);
  pinMode(BUZZER_PIN, OUTPUT);

  if (EEPROM.read(VALID_FLAG_ADDR) == VALID_FLAG) {
    readEEPROMString(SSID_ADDR, stored_ssid, 32);
    readEEPROMString(PASS_ADDR, stored_password, 32);
    readEEPROMString(AP_SSID_ADDR, stored_ap_ssid, 32);
    readEEPROMString(AP_PASS_ADDR, stored_ap_password, 32);
    offline_mode = EEPROM.read(OFFLINE_MODE_ADDR) == 1;
    Serial.println("EEPROM Contents:");
    Serial.print("WiFi SSID: ");
    Serial.println(stored_ssid);
    Serial.print("WiFi Password: ");
    Serial.println(stored_password);
    Serial.print("AP SSID: ");
    Serial.println(stored_ap_ssid);
    Serial.print("AP Password: ");
    Serial.println(stored_ap_password);
    Serial.print("Offline Mode: ");
    Serial.println(offline_mode ? "Enabled" : "Disabled");
  } else {
    Serial.println("No valid credentials in EEPROM, using defaults.");
    strncpy(stored_ssid, default_ssid, 32);
    strncpy(stored_password, default_password, 32);
    strncpy(stored_ap_ssid, default_ap_ssid, 32);
    strncpy(stored_ap_password, default_ap_password, 32);
    offline_mode = false;
  }

  if (offline_mode) {
    Serial.println("Offline mode enabled. Starting AP...");
    startAPMode();
  } else {
    Serial.print("Connecting to ");
    Serial.println(stored_ssid);
    WiFi.begin(stored_ssid, stored_password);

    unsigned long startTime = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - startTime < WIFI_TIMEOUT) {
      delay(500);
      Serial.print(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nWiFi connected.");
      Serial.print("IP address: ");
      Serial.println(WiFi.localIP());

      configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
      Serial.print("Synchronizing time with NTP...");
      int retryCount = 0;
      const int maxRetries = 5;
      while (!time(nullptr) && retryCount < maxRetries) {
        delay(1000);
        Serial.print(".");
        retryCount++;
      }
      if (time(nullptr)) {
        Serial.println("Time synchronized.");
        printLocalTime();
      } else {
        Serial.println("Failed to synchronize time. Using default timestamp.");
      }
      startWebServer();
    } else {
      Serial.println("\nFailed to connect. Starting AP...");
      startAPMode();
    }
  }
}

void loop() {
  server.handleClient();
  unsigned long currentMillis = millis();

  if (WiFi.getMode() == WIFI_STA && WiFi.status() == WL_CONNECTED && !offline_mode) {
    if (Serial2.available()) {
      String data = Serial2.readStringUntil('\n');
      data.trim();

      if (data != "No finger?") {
        int avgIndex = data.indexOf("AVG=");
        int tempIndex = data.indexOf("Temp=");

        if (avgIndex != -1 && tempIndex != -1) {
          String avgStr = data.substring(avgIndex + 4, data.indexOf(' ', avgIndex));
          String tempStr = data.substring(tempIndex + 5, data.indexOf('C', tempIndex));
          float avgValue = avgStr.toFloat();
          float tempValue = tempStr.toFloat();

          if (isValidSensorData(avgValue, tempValue)) {
            Serial.print("AVG: ");
            Serial.println(avgValue);
            Serial.print("Temp: ");
            Serial.println(tempValue);

            if (!fingerDetected) {
              fingerDetected = true;
              fingerStartMillis = currentMillis;
              oneTestSent = false;
              Serial.println("Finger detected, starting timer...");
            }

            if (currentMillis - previousFollowHourMillis >= followHourInterval) {
              sendToSupabase(supabaseTableFollowHour, avgValue, tempValue, "time");
              playBuzzer(1); // Play buzzer once after sending to followhour
              previousFollowHourMillis = currentMillis;
            }

            if ((currentMillis - fingerStartMillis >= 60000) && !oneTestSent) {
              Serial.println("Finger held for 1 minute. Sending to ONETEST...");
              sendToSupabase(supabaseTableOneTest, avgValue, tempValue, "date");
              playBuzzer(3); // Play buzzer three times after sending to onetest
              oneTestSent = true;
            }
          } else {
            Serial.println("Invalid sensor data: BPM or Temp out of range.");
          }
        }
      } else {
        if (fingerDetected) {
          Serial.println("Finger removed. Resetting state and ONETEST timer.");
          fingerStartMillis = 0;
          oneTestSent = false;
        }
        fingerDetected = false;
      }
    }
  } else if (WiFi.getMode() == WIFI_STA && WiFi.status() != WL_CONNECTED && !offline_mode) {
    unsigned long currentTime = millis();
    if (currentTime - lastReconnectAttempt >= RECONNECT_INTERVAL) {
      Serial.println("WiFi disconnected. Attempting to reconnect...");
      WiFi.reconnect();
      lastReconnectAttempt = currentTime;
      reconnectAttempts++;

      unsigned long startTime = millis();
      while (WiFi.status() != WL_CONNECTED && millis() - startTime < WIFI_TIMEOUT) {
        delay(500);
        Serial.print(".");
      }

      if (WiFi.status() == WL_CONNECTED) {
        Serial.println("\nReconnected to WiFi.");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
        reconnectAttempts = 0;
      } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        Serial.println("\nMax reconnection attempts reached. Switching to AP mode...");
        startAPMode();
        reconnectAttempts = 0;
      }
    }
  }
}

void startAPMode() {
  WiFi.mode(WIFI_AP);
  const char* ap_name = strlen(stored_ap_ssid) > 0 ? stored_ap_ssid : default_ap_ssid;
  const char* ap_pass = strlen(stored_ap_password) > 0 ? stored_ap_password : default_ap_password;

  if (strlen(ap_pass) < 8) {
    ap_pass = default_ap_password;
    Serial.println("AP password too short, using default.");
  }

  WiFi.softAP(ap_name, ap_pass);
  Serial.println("AP Mode Started");
  Serial.print("AP SSID: ");
  Serial.println(ap_name);
  Serial.print("AP Password: ");
  Serial.println(ap_pass);
  Serial.print("AP IP address: ");
  Serial.println(WiFi.softAPIP());
  startWebServer();
}

void startWebServer() {
  server.on("/", handleRoot);
  server.on("/wifi", HTTP_POST, handleWiFi);
  server.on("/scan", handleScan);
  server.on("/status", handleStatus);
  server.on("/clear", HTTP_POST, handleClear);
  server.begin();
  Serial.println("Web server started.");
}

void handleRoot() {
  server.send(200, "text/html", html);
}

void handleScan() {
  int n = WiFi.scanNetworks();
  String json = "[";
  for (int i = 0; i < n; ++i) {
    if (i > 0) json += ",";
    json += "{\"ssid\":\"" + WiFi.SSID(i) + "\",\"rssi\":" + String(WiFi.RSSI(i)) + "}";
  }
  json += "]";
  server.send(200, "application/json", json);
}

void handleStatus() {
  String json = "{\"offline_mode\":" + String(offline_mode ? "true" : "false") + "}";
  server.send(200, "application/json", json);
}

void handleWiFi() {
  if (!server.hasArg("plain")) {
    server.send(400, "text/plain", "No data received");
    return;
  }

  StaticJsonDocument<200> doc;
  DeserializationError error = deserializeJson(doc, server.arg("plain"));
  if (error) {
    server.send(400, "text/plain", "Invalid JSON");
    return;
  }

  String new_ssid = "", new_password = "", new_ap_ssid = "", new_ap_password = "";
  bool new_offline_mode = offline_mode;
  bool data_updated = false;

  if (doc.containsKey("ssid") && doc.containsKey("password")) {
    new_ssid = doc["ssid"].as<String>();
    new_password = doc["password"].as<String>();

    if (!isValidSsid(new_ssid)) {
      server.send(400, "text/plain", "Invalid SSID: Must be 1-32 characters and contain no control characters");
      return;
    }

    writeEEPROMString(SSID_ADDR, new_ssid.c_str(), 32);
    writeEEPROMString(PASS_ADDR, new_password.c_str(), 32);
    data_updated = true;
  }

  if (doc.containsKey("ap_ssid") && doc.containsKey("ap_password")) {
    new_ap_ssid = doc["ap_ssid"].as<String>();
    new_ap_password = doc["ap_password"].as<String>();

    if (!isValidSsid(new_ap_ssid)) {
      server.send(400, "text/plain", "Invalid AP SSID: Must be 1-32 characters and contain no control characters");
      return;
    }
    if (!isValidApPassword(new_ap_password)) {
      server.send(400, "text/plain", "Invalid AP password: Must be 8 to 31 characters");
      return;
    }

    writeEEPROMString(AP_SSID_ADDR, new_ap_ssid.c_str(), 32);
    writeEEPROMString(AP_PASS_ADDR, new_ap_password.c_str(), 32);
    data_updated = true;
  }

  if (doc.containsKey("offline_mode")) {
    new_offline_mode = doc["offline_mode"].as<bool>();
    EEPROM.write(OFFLINE_MODE_ADDR, new_offline_mode ? 1 : 0);
    offline_mode = new_offline_mode;
    data_updated = true;
  }

  if (data_updated) {
    EEPROM.write(VALID_FLAG_ADDR, VALID_FLAG);
    EEPROM.commit();
    server.send(200, "text/plain", "Saved. Restarting...");
    delay(1000);
    ESP.restart();
  } else {
    server.send(400, "text/plain", "Invalid data format");
  }
}

void handleClear() {
  clearEEPROM();
}

void sendToSupabase(const char* table, float bpm, float temp, const char* timestampField) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi not connected!");
    return;
  }

  HTTPClient http;
  String url = String(supabaseUrl) + "/rest/v1/" + table;
  http.begin(url);
  http.addHeader("apikey", supabaseKey);
  http.addHeader("Authorization", "Bearer " + String(supabaseKey));
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Prefer", "return=representation");

  StaticJsonDocument<200> doc;
  doc[timestampField] = getCurrentTimestamp();
  doc["bpm_avg"] = bpm;
  doc["temperature"] = temp;

  String jsonData;
  serializeJson(doc, jsonData);

  Serial.println("Payload JSON: " + jsonData);
  Serial.println("Sending data to " + String(table) + "...");

  int httpResponseCode = http.POST(jsonData);
  Serial.println("Response code: " + String(httpResponseCode));
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("Response: " + response);
  } else {
    Serial.println("Error sending data: " + String(httpResponseCode));
  }
  http.end();
}

String getCurrentTimestamp() {
  time_t now = time(nullptr);
  if (now < 100000) {
    Serial.println("Invalid time, returning fallback timestamp");
    return "1970-01-01T00:00:00+07:00";
  }
  char buffer[30];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%S", localtime(&now));
  return String(buffer) + "+07:00";
}
