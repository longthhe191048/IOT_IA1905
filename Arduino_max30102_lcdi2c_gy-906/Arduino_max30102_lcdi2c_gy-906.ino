#include <SoftwareSerial.h>
#include <Wire.h>
#include "MAX30105.h"
#include "heartRate.h"
#include <Adafruit_MLX90614.h>
#include <LiquidCrystal_I2C.h>

// SoftSerial on pins RX=2, TX=3
SoftwareSerial softSerial(2, 3); // RX, TX

// Heart rate and temperature sensors
MAX30105 particleSensor;
Adafruit_MLX90614 tempSensor = Adafruit_MLX90614();

// LCD
LiquidCrystal_I2C lcd(0x27, 16, 2);

// BPM storage
const byte RATE_SIZE = 4;
byte rates[RATE_SIZE];
byte rateSpot = 0;
long lastBeat = 0;
float beatsPerMinute = 0;
int beatAvg = 0;

float temperature = 0;

unsigned long lastLCDUpdate = 0;
unsigned long lastTempRead = 0;
unsigned long lastLog = 0;
unsigned long lastNoFingerMsg = 0;

void setup() {
  softSerial.begin(115200); // Use SoftwareSerial
  Wire.begin();
  
  // LCD
  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Starting...");
  
  // Heart rate sensor
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    softSerial.println("MAX30102 not found");
    lcd.setCursor(0, 1);
    lcd.print("MAX30102 error");
    while (1);
  }
  
  particleSensor.setup();
  particleSensor.setPulseAmplitudeRed(0x0A);
  particleSensor.setPulseAmplitudeGreen(0x00);
  
  // Temperature sensor
  if (!tempSensor.begin()) {
    softSerial.println("MLX90614 not found");
    lcd.setCursor(0, 1);
    lcd.print("Temp sensor error");
    while (1);
  }
  
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Place finger on sensor");
}

void loop() {
  long irValue = particleSensor.getIR();
  
  // Check for finger presence
  if (irValue < 50000) {
    // Reset values when no finger
    beatsPerMinute = 0;
    beatAvg = 0;
    temperature = 0;
    
    lcd.setCursor(0, 0);
    lcd.print("No finger       ");
    lcd.setCursor(0, 1);
    lcd.print("                ");
    
    if (millis() - lastNoFingerMsg >= 500) {
      softSerial.println("No finger?");
      lastNoFingerMsg = millis();
    }
    return;
  }
  
  // Detect heartbeat
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
  
  // Read temperature every 1s
  if (millis() - lastTempRead >= 1000) {
    temperature = tempSensor.readObjectTempC();
    lastTempRead = millis();
  }
  
  // Log to SoftSerial every 500ms
  if (millis() - lastLog >= 500) {
    softSerial.print("IR=");
    softSerial.print(irValue);
    softSerial.print(" BPM=");
    softSerial.print(beatsPerMinute, 1);
    softSerial.print(" AVG=");
    softSerial.print(beatAvg);
    softSerial.print(" Temp=");
    softSerial.print(temperature, 1);
    softSerial.println("C");
    
    lastLog = millis();
  }
  
  // Update LCD every 500ms
  if (millis() - lastLCDUpdate >= 500) {
    lcd.setCursor(0, 0);
    lcd.print("BPM: ");
    if (beatAvg > 30 && beatAvg < 180)
      lcd.print(beatAvg);
    else
      lcd.print("-- ");
    lcd.print("     ");
    
    lcd.setCursor(0, 1);
    lcd.print("Temp: ");
    lcd.print(temperature, 1);
    lcd.print((char)223);
    lcd.print("C  ");
    
    lastLCDUpdate = millis();
  }
}
