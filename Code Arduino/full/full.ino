#include <Arduino.h>
#include <WiFi.h>
#include "esp_camera.h"
#include <PubSubClient.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include <ThingsBoard.h>
#include <Arduino_MQTT_Client.h>
#define LED1 2 // GPIO 2 in the ESP (for the LED)
#define LED2 14
#define RELAY 15
#define THINGSBOARD_SERVER  "demo.thingsboard.io" // ThingsBoard server
#define TOKEN  "NN3cHp8la9GcJLvJWlYh" // ThingsBoard token
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"
const char* wifiSSID = "@Tuanvu";     // Enter your WiFi SSID
const char* wifiPass = "12345677"; // Enter your WiFi password
const char* mqttBroker = "broker.hivemq.com";      // MQTT broker address

void startCameraServer();
void setupLedFlash(int pin);

constexpr uint16_t MAX_MESSAGE_SIZE = 128U ;
WiFiClient client;
PubSubClient mqtt(client);
WiFiClient espClient;
Arduino_MQTT_Client mqttClient(espClient);
ThingsBoard tb(mqttClient, MAX_MESSAGE_SIZE);

void connectWifi();
void connect_mqtt(); 
void mqttReceive(char *topic, byte*msg, unsigned int msgLength);
void connectToThingsBoard() {
  if (!tb.connected()) {
    Serial.println("Connecting to ThingsBoard server");
    
    if (!tb.connect(THINGSBOARD_SERVER, TOKEN)) {
      Serial.println("Failed to connect to ThingsBoard");
    } else {
      Serial.println("Connected to ThingsBoard");
    }
  }
}
void setup()
{
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Disable brownout detector
    
    pinMode(LED1, OUTPUT); // Set the LED1 pin as an OUTPUT
    pinMode(LED2, OUTPUT);
    pinMode(RELAY, OUTPUT);
    Serial.begin(115200);   
    mqtt.setServer(mqttBroker, 1883);
    mqtt.setCallback(mqttReceive);
   Serial.setDebugOutput(true);
  Serial.println();

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.frame_size = FRAMESIZE_UXGA;
  config.pixel_format = PIXFORMAT_JPEG; // for streaming
  //config.pixel_format = PIXFORMAT_RGB565; // for face detection/recognition
  config.grab_mode = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 12;
  config.fb_count = 1;
  
  // if PSRAM IC present, init with UXGA resolution and higher JPEG quality
  //                      for larger pre-allocated frame buffer.
  if(config.pixel_format == PIXFORMAT_JPEG){
    if(psramFound()){
      config.jpeg_quality = 10;
      config.fb_count = 2;
      config.grab_mode = CAMERA_GRAB_LATEST;
    } else {
      // Limit the frame size when PSRAM is not available
      config.frame_size = FRAMESIZE_SVGA;
      config.fb_location = CAMERA_FB_IN_DRAM;
    }
  } else {
    // Best option for face detection/recognition
    config.frame_size = FRAMESIZE_QVGA;
#if CONFIG_IDF_TARGET_ESP32S3
    config.fb_count = 2;
#endif
  }

#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  // camera init
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x", err);
    return;
  }

  sensor_t * s = esp_camera_sensor_get();
  // initial sensors are flipped vertically and colors are a bit saturated
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1); // flip it back
    s->set_brightness(s, 1); // up the brightness just a bit
    s->set_saturation(s, -2); // lower the saturation
  }
  // drop down frame size for higher initial frame rate
  if(config.pixel_format == PIXFORMAT_JPEG){
    s->set_framesize(s, FRAMESIZE_QVGA);
    s->set_quality(s, 15);
  }

#if defined(CAMERA_MODEL_M5STACK_WIDE) || defined(CAMERA_MODEL_M5STACK_ESP32CAM)
  s->set_vflip(s, 1);
  s->set_hmirror(s, 1);
#endif

#if defined(CAMERA_MODEL_ESP32S3_EYE)
  s->set_vflip(s, 1);
#endif

// Setup LED FLash if LED pin is defined in camera_pins.h
#if defined(LED_GPIO_NUM)
  setupLedFlash(LED_GPIO_NUM);
#endif

  WiFi.begin(wifiSSID, wifiPass);
  WiFi.setSleep(false);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");

  startCameraServer();

  Serial.print("Camera Ready! Use 'http://");
  Serial.print(WiFi.localIP());
  Serial.println("' to connect");
  connectToThingsBoard ();
}

void loop()
{
    if (!mqtt.connected()) {
        connect_mqtt();
        Serial.println("MQTT Connected");
    }
    mqtt.loop();
    delay(100);

    if (!tb.connected()) {
        connectToThingsBoard ();
    }

    tb.loop();
}

void connect_mqtt() {
    while (!mqtt.connected()) {
        Serial.println("Connecting to MQTT...");
        if (mqtt.connect("mqtt_test")) {
            mqtt.subscribe("yourtopic"); // Subscribe to the MQTT topic
        }
    }
}
void mqttReceive(char *topic, byte* msg, unsigned int msgLength) {
    String data;
    for (int i = 0; i < msgLength; i++) {
        data += (char)msg[i];
    }

    Serial.print("Received message: ");
    Serial.println(data);  // In giá trị nhận được từ MQTT

    int value = data.toInt();  // Chuyển thông điệp nhận được sang số nguyên
    
    // In giá trị sau khi chuyển thành số
    Serial.print("Processed value: ");
    Serial.println(value);
    
    // Điều khiển LED dựa trên giá trị nhận được
    switch (value) {
        case 0:
            digitalWrite(LED1, LOW);  // Tắt LED
            Serial.println("LED1 turned OFF");  // In thông báo tắt LED
            break;
        
        case 1:
            digitalWrite(LED1, HIGH);  // Bật LED
            Serial.println("LED1 turned ON");  // In thông báo bật LED
            break;
        case 2:
            digitalWrite(LED2, HIGH);  // Bật LED
            Serial.println("LED2 turned ON");  // In thông báo bật LED
            break;
        case 3:
            digitalWrite(LED2, LOW);  // Bật LED
            Serial.println("LED2 turned OFF");  // In thông báo bật LED
            break;
        case 4:
            digitalWrite(LED1, HIGH);  // Bật LED
            digitalWrite(LED2, HIGH);
            digitalWrite(RELAY, HIGH);
            Serial.println("LED1 LED2 RELAY turned ON");  // In thông báo bật LED
            break;
        case 5:
            digitalWrite(LED1, LOW);  // Bật LED
            digitalWrite(LED2, LOW);
            digitalWrite(RELAY, LOW);
            Serial.println("LED1 LED2 RELAY turned OFF");  // In thông báo bật LED
            break;
        case 6:
            digitalWrite(RELAY, HIGH);  // Bật LED
            Serial.println("RELAY turned ON");  // In thông báo bật LED
            break;
        case 7:
            digitalWrite(RELAY, LOW);  // Bật LED
            Serial.println("RELAY turned OFF");  // In thông báo bật LED
            break;    
        default:
            Serial.println("Invalid value received");  // Thông báo khi giá trị không hợp lệ
            break;
    }
    // Gửi dữ liệu lên ThingsBoard
    tb.sendTelemetryData("LED1 Status", digitalRead(LED1));
    tb.sendTelemetryData("LED2 Status", digitalRead(LED2)); 
    tb.sendTelemetryData("Relay Status", digitalRead(RELAY));
}