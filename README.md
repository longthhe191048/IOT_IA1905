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

This remote health monitoring system is designed to collect vital signs such as body temperature and heart rate using biomedical sensors. Data is displayed on an LCD screen and a web/app interface, allowing doctors to monitor and provide feedback remotely. All data is stored in real time in a cloud database and can be exported as Excel sheets for analysis and reporting.

The project supports remote healthcare, especially in regions with limited medical staff or during pandemics.

---

## I. Project Introduction

### I.1. Motivation

There is a growing demand for remote health monitoring, especially in pandemics or areas with medical staff shortages. Vital signs such as heart rate and body temperature need to be monitored continuously. Automation and remote data access can ease the burden on the healthcare system.

### I.2. Project Overview

- Measures heart rate and temperature using sensors
- Displays data on LCD and Web/App
- Enables doctors to monitor remotely

---

## II. System Analysis and Design

### II.1. Hardware Design

| Device               | Description                                                      |
|----------------------|------------------------------------------------------------------|
| **ESP32**            | Wi-Fi module with integrated microcontroller                     |
| **Arduino Uno**      | Main control board; reads data from sensors and communicates with ESP32 |
| **MAX30102**         | Heart rate sensor                                                |
| **GY-906 MLX90614**  | Temperature sensor                                               |
| **LCD I2C 16x2**     | Displays heart rate and temperature                              |
| **Breadboard & wires** | Flexible connections for components                             |

#### Circuit Diagram

> *[Include image here if applicable]*

#### Schematic Diagram

> *[Include image here if applicable]*

---

### II.2. Software Design

#### Algorithm Flowchart

> *[Include diagram if available]*

#### Key Functions

- **Heart Rate Detection**: Calculates beats per minute and averages recent readings for stability.
- **Temperature Measurement**: Measures user’s temperature every 1 second and stores it in a variable.

---

## III. Experiment & Evaluation

### III.1. Experiment

- Hands-on test using biomedical sensors  
- Video documentation of the test (touch-based measurement)

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

## 👥 Contact

For further details or collaboration, please contact the project team via the Telegram Bot or reach out through the course platform.

