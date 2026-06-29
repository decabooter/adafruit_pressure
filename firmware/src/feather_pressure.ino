#include <Wire.h>
#include <Adafruit_BMP5xx.h>
#include <ArduinoJson.h>
#include <ArduinoMqttClient.h>
#include <WiFi101.h>

#include "config.h"
#include "secrets.h"

Adafruit_BMP5xx bmp;
WiFiClient      wifiClient;
MqttClient      mqttClient(wifiClient);

char          mqttTopic[64];
unsigned long epochAtSync  = 0;
unsigned long millisAtSync = 0;
unsigned long lastReadMs   = 0;

// ---------------------------------------------------------------------------

void setup() {
    Serial.begin(115200);
    Serial.println("=== BOOT ===");
    Serial.flush();

    Serial.println("DEBUG: Initializing I2C...");
    Wire.begin();
    Serial.println("DEBUG: I2C OK.");
    Serial.flush();

    Serial.println("DEBUG: Scanning I2C bus for devices...");
    Serial.flush();
    bool anyFound = false;
    for (byte addr = 1; addr < 127; addr++) {
        Wire.beginTransmission(addr);
        byte err = Wire.endTransmission();
        if (err == 0) {
            Serial.print("DEBUG: I2C device found at 0x");
            if (addr < 16) Serial.print("0");
            Serial.println(addr, HEX);
            Serial.flush();
            anyFound = true;
        }
    }
    if (!anyFound) {
        Serial.println("DEBUG: No I2C devices found at all — check SDA/SCL wiring.");
        Serial.flush();
    }

    Serial.println("DEBUG: Initializing BMP5xx sensor...");
    Serial.flush();
    if (!bmp.begin((uint8_t)0x47)) {
        Serial.println("ERROR: BMP5xx not found. Check wiring (SDA/SCL/VIN/CS).");
        Serial.flush();
        while (1) {
            Serial.println("HALT: sensor not found — check wiring, then reset.");
            Serial.flush();
            delay(3000);
        }
    }
    Serial.println("DEBUG: BMP5xx found OK.");
    bmp.setTemperatureOversampling(BMP5XX_OVERSAMPLING_2X);
    bmp.setPressureOversampling(BMP5XX_OVERSAMPLING_16X);
    bmp.setIIRFilterCoeff(BMP5XX_IIR_FILTER_COEFF_3);
    Serial.println("DEBUG: BMP5xx configured.");
    Serial.flush();

    WiFi.setPins(8, 7, 4, 2);  // CS, IRQ, RST, EN for Feather M0 WiFi
    connectWiFi();
    syncNTP();
    snprintf(mqttTopic, sizeof(mqttTopic), "pressure/%s/reading", DEVICE_ID);
    connectMQTT();

    Serial.println("=== Ready. ===");
    Serial.flush();
}

void loop() {
    // Heartbeat so we can confirm the board is alive even if nothing else prints
    static unsigned long lastHeartbeat = 0;
    if (millis() - lastHeartbeat >= 3000) {
        lastHeartbeat = millis();
        Serial.print("DEBUG: loop alive, uptime=");
        Serial.print(millis() / 1000);
        Serial.println("s");
        Serial.flush();
    }

    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("DEBUG: WiFi lost, reconnecting...");
        connectWiFi();
        syncNTP();
    }

    if (!mqttClient.connected()) {
        Serial.println("DEBUG: MQTT disconnected, reconnecting...");
        connectMQTT();
    }
    mqttClient.poll();

    unsigned long now = millis();
    if (now - lastReadMs >= READ_INTERVAL_MS) {
        lastReadMs = now;
        readAndPublish();
    }
}

// ---------------------------------------------------------------------------

void connectWiFi() {
    Serial.print("DEBUG: ATWINC1500 firmware version: ");
    Serial.println(WiFi.firmwareVersion());
    Serial.flush();
    Serial.print("DEBUG: Connecting to WiFi SSID: ");
    Serial.println(WIFI_SSID);
    Serial.flush();
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        Serial.flush();
        if (++attempts % 20 == 0) {
            Serial.print(" status=");
            Serial.println(WiFi.status());
            Serial.flush();
        }
    }
    Serial.println();
    Serial.print("DEBUG: WiFi connected. IP: ");
    Serial.println(WiFi.localIP());
    Serial.flush();
}

void syncNTP() {
    Serial.print("DEBUG: Waiting for NTP");
    Serial.flush();
    for (int i = 0; i < 10; i++) {
        epochAtSync = WiFi.getTime();
        if (epochAtSync != 0) {
            millisAtSync = millis();
            Serial.print(" OK. Epoch=");
            Serial.println(epochAtSync);
            Serial.flush();
            return;
        }
        delay(1000);
        Serial.print(".");
        Serial.flush();
    }
    Serial.println(" WARN: NTP unavailable, using millis() fallback.");
    Serial.flush();
}

void connectMQTT() {
    mqttClient.setUsernamePassword(MQTT_USER, MQTT_PASS);
    Serial.print("DEBUG: Connecting to MQTT broker ");
    Serial.print(MQTT_BROKER);
    Serial.print(":");
    Serial.println(MQTT_PORT);
    Serial.flush();
    int attempts = 0;
    while (!mqttClient.connect(MQTT_BROKER, MQTT_PORT)) {
        Serial.print("DEBUG: MQTT connect failed, error=");
        Serial.print(mqttClient.connectError());
        Serial.println(". Retrying in 5s...");
        Serial.flush();
        delay(5000);
        if (++attempts > 10) {
            Serial.println("DEBUG: MQTT still unreachable after 10 attempts. Continuing...");
            Serial.flush();
            return;
        }
    }
    Serial.println("DEBUG: MQTT connected.");
    Serial.flush();
}

uint64_t timestampMs() {
    if (epochAtSync == 0) return (uint64_t)millis();
    return (uint64_t)epochAtSync * 1000ULL + (millis() - millisAtSync);
}

void readAndPublish() {
    Serial.println("DEBUG: Reading sensor...");
    Serial.flush();
    if (!bmp.performReading()) {
        Serial.println("ERROR: BMP5xx performReading() failed.");
        Serial.flush();
        return;
    }

    float pressure_hpa = bmp.pressure;  // library already returns hPa
    float temp_c       = bmp.temperature;

    Serial.print("DEBUG: Raw pressure_hpa=");
    Serial.print(pressure_hpa);
    Serial.print(" temp_c=");
    Serial.println(temp_c);
    Serial.flush();

    if (pressure_hpa < 800.0F || pressure_hpa > 1200.0F) {
        Serial.print("WARN: Pressure out of range: ");
        Serial.println(pressure_hpa);
        Serial.flush();
        return;
    }
    if (temp_c < -40.0F || temp_c > 85.0F) {
        Serial.print("WARN: Temperature out of range: ");
        Serial.println(temp_c);
        Serial.flush();
        return;
    }

    StaticJsonDocument<128> doc;
    doc["device_id"]    = DEVICE_ID;
    doc["ts"]           = timestampMs();
    doc["pressure_hpa"] = roundf(pressure_hpa * 100.0F) / 100.0F;
    doc["temp_c"]       = roundf(temp_c * 10.0F) / 10.0F;

    char payload[128];
    serializeJson(doc, payload);

    Serial.print("DEBUG: Publishing: ");
    Serial.println(payload);
    Serial.flush();

    mqttClient.beginMessage(mqttTopic);
    mqttClient.print(payload);
    mqttClient.endMessage();

    Serial.println("DEBUG: Published OK.");
    Serial.flush();
}
