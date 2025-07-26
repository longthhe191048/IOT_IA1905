# Remote Patient Health Monitoring System

## Course Project Report – IoT 102

- **Class**: IA1905  
- **Team Members**:
  1. Trần Hoàng Long  
  2. Nguyễn Công Hiếu  
  3. Trần Thị Ngọc Lan  
  4. Trần Thanh Bảo Phúc  
- **Instructor**: Đặng Minh Đức  
- **External Advisor**: None  

**Hà Nội, July 27, 2025**

---

## 📌 Project Summary

The remote health monitoring system is designed to collect vital signs from patients, such as body temperature and heart rate, using biomedical sensors. Data is displayed on an LCD screen and through a Web/App interface, allowing doctors to monitor and respond remotely. All data is stored in real-time in a database, which can be exported as spreadsheets (Excel) for analysis and reporting. The system also integrates a buzzer to emit signals when data is successfully sent to the database. 

The project supports remote healthcare, especially in regions with limited medical staff or during pandemics.

---

## I. Project Introduction

### I.1. Motivation

The increasing demand for remote health monitoring, driven by pandemics and limited healthcare access in underserved regions, necessitates automated systems for monitoring vital signs like heart rate and temperature. This project aims to alleviate pressure on healthcare systems by enabling real-time, remote data access.

### I.2. Project Overview

- The system reads and records heart rate and temperature using sensors.
- Displays the data on an LCD and a Web/App interface.
- Allows doctors to remotely monitor the patient's vital signs.

<img width="940" height="481" alt="image" src="https://github.com/user-attachments/assets/333c091d-dd42-4b79-be10-6839afdf73b7" />

---

## II. System Analysis and Design

### II.1. Hardware Design

| Device               | Description                                                      |
|----------------------|------------------------------------------------------------------|
| **ESP32**            | Wi-Fi module with integrated microcontroller                     |
| **Arduino Uno**      | Main control board; reads data from sensors and communicates with ESP32 |
| **MAX30102**         | Heart rate sensor                                                |
| **GY-906 MLX90614**  | Temperature sensor                                               |
| **Buzzer**           | Provides audible feedback for successful data transmission       |
| **LCD I2C 16x2**     | Displays heart rate and temperature                              |
| **Breadboard & wires** | Flexible connections for components                             |

#### Circuit Diagram

<img width="918" height="533" alt="image" src="https://github.com/user-attachments/assets/db3c085b-c877-48b1-9ac7-a03e236375f9" />

#### Schematic Diagram

<img width="913" height="636" alt="image" src="https://github.com/user-attachments/assets/bc12ae63-8235-4dc8-bc5f-abdf4e84cdd1" />

---

### II.2. Software Design

#### Algorithm Flowchart

<img width="954" height="732" alt="image" src="https://github.com/user-attachments/assets/7b17994f-98cb-4900-8079-f91ad9c271ee" />

#### Key Functions

- **Heart Rate Detection**: Calculates beats per minute and averages recent readings for stability.
  
```
  if (checkForBeat(irValue)) {
    long delta = millis() - lastBeat;
    lastBeat = millis();
    
    beatsPerMinute = 60 / (delta / 1000.0);
    
    if (beatsPerMinute > 20 && beatsPerMinute < 255) {
      rates[rateSpot++] = (byte)beatsPerMinute;
      rateSpot %= RATE_SIZE;
      
      beatAvg = 0;
      for (byte x = 0; x < RATE_SIZE; x++)
        beatAvg += rates[x];
      beatAvg /= RATE_SIZE;
    }
  }
```

- **Temperature Measurement**: Measures user’s temperature every 1 second and stores it in a variable.

```
  // Read temperature every 1s
  if (millis() - lastTempRead >= 1000) {
    temperature = tempSensor.readObjectTempC();
    lastTempRead = millis();
  }
```

---

## III. Experiment & Evaluation

### III.1. Experiment

Video of the experiment: [Sensor-based testing demonstration](https://drive.google.com/drive/folders/14AeoBDOAd2g8ZjJYt7ODGIy9jfw0am6b).

### III.2. Results

- Fully assembled and stable system
- Accurate operation of sensors for heart rate and temperature
- Real-time display on LCD and synced to Supabase database
- Web interface allows remote monitoring
- Data exportable to Excel for tracking and reporting

#### Telegram Integration

- A Telegram bot sends automated alerts and responds to user queries
- Enhances mobile accessibility for health updates

#### Data Access

- Downloadable spreadsheets:
  - `one Test`
  - `follow Hour`

---

## IV. Future Development

### IV.1. Funding & Development Model

- Crowdfunding via Kickstarter or Patreon
- Dual model:
  - Open source
  - Paid services

### IV.2. Hardware & Sensor Upgrades

- Track 5 vital signs: pulse/heart rate, body temperature, blood pressure, respiration rate, SpO₂
- Use higher-precision medical-grade sensors
- Redesigned circuitry for medical environments
- Independent sensor operation
- Add power backup for portability

### IV.3. Connectivity & Communication

- SIM card support, SMS alerts, mobile data, Bluetooth
- Patient identification via ID or NFC cards
- Integration with hospital databases

### IV.4. Database & Management System

- Dedicated database and server
- Alerting system for abnormal readings
- Role-based access for doctors, patients, admins

### IV.5. Software & Interface

- Custom app for better security and flexibility
- Data visualization on web/app
- Emergency alert features (manual button or automatic trigger)
- OTA updates via Wi-Fi or mobile

### IV.6. Product Versions & Optimization

- Two product lines: general monitoring and ICU-level monitoring
- Cost optimization for wider access

---

## V. Appendix

### V.1. Links

- [Presentation Slides (Canva)](https://www.canva.com/design/DAGtuN_zcZg/F0IDgzr--heltMMNk1S87A/edit?utm_content=DAGtuN_zcZg&utm_campaign=designshare&utm_medium=link2&utm_source=sharebutton)
- [Web testing link](https://longthhe191048.tech)
- [Telegram bot](https://t.me/iot_su25_ia1905_bot)

---
## 🔧 Folder Structure

```
.
├── arduino/                      # Arduino Uno firmware (MAX30102, MLX90614, LCD)
│   └── Arduino_max30102_lcdi2c_gy-906.ino
│
├── esp32/                        # ESP32 firmware for Wi-Fi + Supabase upload
│   └── Final_Health_Monitoring_ESP32.ino
│
├── web/                          # Web dashboard (HTML + JS + Supabase integration)
│   ├── index.html
│   ├── admin.html
│   ├── redirect.html
│   └── user.html
│
├── telegram/                     # Telegram bot server (Python)
│   ├── main.py
│   ├── requirements.txt
│   └── .env.example              # Example environment config
│
├── docs/                         # Diagrams, report, and presentation
│   ├── IOT102_Project Report_EN.pdf
│   └── IOT102_Project Report_VN.pdf
│
├── LICENSE                       # MIT License
├── README.md                     # This readme
└── .gitignore                    # Ignore compiled files and secrets
```

---

## 🛠️ Technology Stack

- **Microcontrollers**: ESP32, Arduino Uno  
- **Sensors**: MAX30102 (Heart Rate), MLX90614 (Temperature)  
- **Display**: LCD I2C  
- **Connectivity**: Wi-Fi (ESP32), Telegram API  
- **Database**: Supabase  
- **Frontend**: Web interface (custom)  
- **Integration**: Telegram Bot, Excel Export  

---

## 🚀 How to Deploy

### 1. Hardware Setup
- Connect the MAX30102 and GY-906 sensors to the Arduino Uno.
- Connect the LCD I2C display to the Arduino Uno.
- Connect the Arduino Uno to the ESP32 via SoftwareSerial on pins 2 (RX) and 3 (TX) of the Arduino, and pins 16 (RX) and 17 (TX) on the ESP32.
- Connect the buzzer to ESP32 (pin 5).

### 2. Supabase Setup
1. Go to [Supabase](https://supabase.com/) and create a new project.
2. Go to the `SQL Editor` and run the following queries to create the necessary tables:

```sql
-- Create the table for hourly data
CREATE TABLE followhour (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "time" TIMESTAMPTZ DEFAULT now() NOT NULL,
    bpm_avg REAL,
    temperature REAL
);

-- Create the table for daily test data
CREATE TABLE onetest (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    "date" TIMESTAMPTZ DEFAULT now() NOT NULL,
    bpm_avg REAL,
    temperature REAL
);

-- Create user profiles table
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    "role" TEXT DEFAULT 'user' -- user, admin
);
```
3. In your Supabase project, go to `Authentication` -> `Providers` and enable `Google`.
4. Go to `Settings` -> `API` and copy your `URL` and `anon key`. You will need these for the ESP32, web, and Telegram configurations.

### 3. Arduino Firmware
1. Open the `Arduino_max30102_lcdi2c_gy-906/Arduino_max30102_lcdi2c_gy-906.ino` file in the Arduino IDE.
2. Install the required libraries: `MAX30105`, `Adafruit_MLX90614`, `LiquidCrystal_I2C`.
3. Upload the sketch to your Arduino Uno.

### 4. ESP32 Firmware
1. Open `Final_Health_Monitoring_ESP32/Final_Health_Monitoring_ESP32.ino` in the Arduino IDE.
2. Make sure you have the ESP32 board manager installed.
3. Install the required libraries: `ArduinoJson`.
4. Update the following variables with your Supabase credentials:
   ```cpp
   const char* supabaseUrl = "YOUR_SUPABASE_URL";
   const char* supabaseKey = "YOUR_SUPABASE_ANON_KEY";
   ```
5. The ESP32 will start in AP (Access Point) mode. Connect to the "Health monitor V1" Wi-Fi network (password: `YOUR_AP_PASSWORD`) and configure your Wi-Fi credentials through the web interface at `192.168.4.1`.
6. Upload the sketch to your ESP32.

### 5. Web Interface
1. Open the following files and replace `"YOUR_SUPABASE_URL"` and `"YOUR_SUPABASE_ANON_KEY"` with your Supabase API credentials:
   - `web/admin.html`
   - `web/index.html`
   - `web/redirect.html`
   - `web/user.html`
2. Deploy the `web` folder to a static hosting service like Netlify, Vercel, or GitHub Pages.

### 6. Telegram Bot
1. Create a new Telegram bot by talking to the [BotFather](https://t.me/botfather) on Telegram. Copy the bot token.
2. In the `telegram` directory, create a `.env` file from the `.env.example` and add your credentials:
   ```
   TELEGRAM_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
   SUPABASE_URL=YOUR_SUPABASE_URL
   SUPABASE_KEY=YOUR_SUPABASE_ANON_KEY
   ```
3. Install the Python dependencies:
   ```bash
   pip install -r telegram/requirements.txt
   ```
4. Run the bot:
   ```bash
   python telegram/main.py
   ```
5. It is recommended to deploy this bot to a service like Heroku or a VPS for continuous operation.

---
## 🧾 License

This project is licensed under the **MIT License** — you are free to use, modify, and distribute this software. See [`LICENSE`](./LICENSE) for details.

---
## 🤝 Contributing

We welcome contributors!

1. **Fork** this repository
2. Create a **feature branch** (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m 'Add my feature'`)
4. Push to GitHub (`git push origin feature/my-feature`)
5. Open a **Pull Request**

---
## 👥 Contact

For further details or collaboration, please contact the project leader through:
- **Email**: hoanglong2712005@gmail.com  
- **Facebook**: [fb.me/wdchocopie](https://fb.me/wdchocopie)  
- **LinkedIn**: [linkedin.com/in/wdchocopie](https://www.linkedin.com/in/wdchocopie/)
