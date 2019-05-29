# EVNotiPi
Python Version of EVNotify

## Needed Hardware
- Diamex OBD-Hat  https://www.diamex.de/dxshop/PI-OBD-HAT-OBD2-Modul-fuer-Raspberry-PI with flat connector
- Raspberry Pi Zero W with GPIO Header  https://www.rasppishop.de/Raspberry-Pi-Zero-W-inkl-40-Pin-GPIO-Header
- OTG cable for Raspberry Pi  https://www.rasppishop.de/Raspberry-Pi-Zero-USB-Adapter-Kabel
- DC/DC Step-Down Converter  https://www.aliexpress.com/item/5-pcs-Ultra-Small-Size-DC-DC-Step-Down-Power-Supply-Module-3A-Adjustable-Step-Down/32261885063.html?spm=a2g0s.9042311.0.0.57094c4dLTzDDA
- Wemos D1 mini  https://www.aliexpress.com/item/D1-mini-Mini-NodeMcu-4M-bytes-Lua-WIFI-Internet-of-Things-development-board-based-ESP8266/32529101036.html?spm=a2g0x.10010108.1000001.12.71c46d4fQAgD9Q
- Wemos Ralay Shield  https://www.aliexpress.com/item/1PCS-NEW-Relay-Shield-for-Arduino-WeMos-D1-Mini-ESP8266-Development-Board-WeMos-D1-Relay-Module/32737849680.html?spm=a2g0o.productlist.0.0.2aae2b26AhbDEs&ws_ab_test=searchweb0_0%2Csearchweb201602_10%2Csearchweb201603_52&algo_pvid=5e7c779b-c82a-480b-bdb6-50121bd34f8a&btsid=84c71f9f-6e18-48a9-8f54-6813abeee7ff&algo_expid=5e7c779b-c82a-480b-bdb6-50121bd34f8a-0
- Resistor 1,2MOhm 1/4W
- some heat shrink tube
- small wires in different colors
- 4 screws M2,5x15 (to fix the OBD-Hat into the case)
- 5 screws M2,5x8 self-cutting (for the case)
- Case  https://www.thingiverse.com/thing:3660666 
- LTE Stick Huawai E3372  https://www.amazon.de/gp/product/B011BRKPLE/

## Wemos Sketch
Use Arduino IDE to program the Wemos with the following sketch

/*
  ESP8266 Wemos by Kevin Wieland for EVNotiPi
  Recognizes voltage above 12.75V and turns Relay on (Rpi).
  Shutdown and turns off
  Relay Hat on Wemos D1 Mini.
  D1 to GPIO24 Rpi
  A0 with 1,2M resistor to +12V
  
*/
#include <ESP8266WiFi.h>
const int rpiPin = D1;
const int offPin = D0;
int pistat = 0;
int counter = 0;
void setup() {
  pinMode(rpiPin, OUTPUT);
  pinMode(offPin, OUTPUT);
  digitalWrite(offPin, LOW);
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();
}
void loop() {
  delay(2000); 
  int sensorValue = analogRead(A0);
  float voltage = sensorValue * (15.88 / 1023.0);                  
  if ( voltage > 12.75 )
  {
    if ( pistat == 0 )
    {
      counter == 0;
      digitalWrite(rpiPin, HIGH);
      delay(60000 );
      pistat = 1;
    } 
  }
  else
  {
      if ( pistat == 1)
      {
        counter = counter + 1;
        if ( counter > 150 )
        {
          digitalWrite(offPin, HIGH);
          delay(3000);
          digitalWrite(offPin, LOW);
          delay(40000);
          counter = 0;
          digitalWrite(rpiPin, LOW);
          pistat = 0;
        }
      }
   }
}


## Drawings

![Drawing](url)

## Prerequisites
- Python 3
- Python Serial
- Python GPS
- GPSd
- EVNotify API Python Library

## Installation
### Raspberry Pi
- `sudo apt-get update`
- `sudo apt-get upgrade`
- `sudo apt-get install python python-serial python-gps gpsd`
### EVNotiPi
- Copy `config.template.json` to `config.json`. Adjust the values for your needs

