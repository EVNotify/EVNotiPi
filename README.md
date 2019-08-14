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
```C
/*
  
  ESP8266 Wemos by Kevin Wieland for EVNotiPi
  adjusted by Mario Mueller
  Recognizes voltage above 12.75V and turns Relay on (Rpi).
  Shutdown and turns off
  Relay Hat on Wemos D1 Mini.
  D0 to GPIO24 Rpi
  A0 with 1.2MOhm resistor to +12V
  
*/
#include <ESP8266WiFi.h>
const int relayPin = D1;
const int shutdownPin = D0;
//if you need to adjust the voltage reading - measure the voltage with a mulitmeter, connected and adjust these values
const float trueValue=12.28;
const float displayedValue=11.98;

int pistat = 0;
int voltageLowCounter = 0;
int voltageHighCounter = 0;

void setup() {
  Serial.begin(9600);
  pinMode(relayPin, OUTPUT);
  pinMode(shutdownPin, OUTPUT);
  digitalWrite(shutdownPin, LOW);
  WiFi.mode(WIFI_OFF);
  WiFi.forceSleepBegin();
}
void loop() {
  delay(2000);                                                
  int sensorValue = analogRead(A0);
  float voltage = sensorValue * 0.0144 * ((100/displayedValue*trueValue)/100);
  Serial.print("Sensor Value: ");
  Serial.println(sensorValue);
  Serial.print("Voltage: ");
  Serial.println(voltage);    
  Serial.print("voltageLowCounter: ");
  Serial.println(voltageLowCounter);
  Serial.print("voltageHighCounter: ");
  Serial.println(voltageHighCounter);              
  if ( voltage > 12.75 )                           
  {
    if ( pistat == 0 )
    {
      voltageLowCounter = 0;
      Serial.println("Power up Rpi");
      digitalWrite(relayPin, HIGH);
      delay(60000);                                        
      pistat = 1;
    } 
    else                    
    {if (voltageHighCounter == 30)    //if voltage is High for a minute - reset voltageLowCounter
        {voltageHighCounter=0;
         voltageLowCounter=0;
        }
      voltageHighCounter++;
    }
    
  }
  else
  {
      if ( pistat == 1)
      {
        voltageLowCounter++;
        voltageHighCounter=0;
        if ( voltageLowCounter > 150 )                        
        {
          Serial.println("initiate sutdown");
          digitalWrite(shutdownPin, HIGH);
          delay(3000);                        
          digitalWrite(shutdownPin, LOW);
          delay(40000);                                    
          voltageLowCounter = 0;
          Serial.println("Rpi off"); 
          digitalWrite(relayPin, LOW);
          pistat = 0;
        }
      }
   }
}
```

## Drawings

![Drawing](https://evnotify.de/public/EVNotiPi/plan.jpg)

## Prerequisites
- Python 3
- Python Serial
- Python GPS
- GPSd
- EVNotify API Python Library

## Installation
### Raspberry Pi

- sudo apt-get install python python-serial python-gps gpsd

- sudo apt-get update

- sudo apt-get upgrade

- sudo apt-get install git

- sudo apt install python3-pip 

- sudo pip3 install gps

- sudo pip3 install gpio

- sudo pip3 install pyserial

- sudo pip3 install pexpect

- sudo raspi-config
```
--> 5 Inetrface Options
	--> P6 Serial
		--> no--> yes -->OK
			-->finish-->reboot
 ```

- sudo mkdir /var/www
```
	-->sudo mkdir /var/www/html
		-->cd /var/www/html/
```

- sudo nano /boot/config.txt
```
-->dtoverlay=pi3-disable-bt
   enable_uart=1
```

- sudo git clone --recurse-submodules https://github.com/EVNotify/EVNotiPi

- cd /var/www/html/EVNotiPi/

- sudo nano config.template.json
```
{
    "akey": "xxxxxx",
    "token": "xxxxxxxxxxxxxxxxxxxx",
    "cartype": "IONIQ_BEV",
    "dongle": {
            "type": "PiOBD2Hat",
            "port": "/dev/ttyAMA0",
            "speed": 115200
    }
}
```
```
srtg+x
	--> y
		change file name to config.json
```
- sudo python3 evnotipi.py &


- cd /var/www/html/EVNotiPi/runs/

- sudo nano runs.sh
```
--> check and adjust paths
```

- sudo nano atreboot.sh

```
--> check and adjust paths
```

- sudo chmod 755 runs.sh

- sudo chmod 755 atreboot.sh

- cd

- sudo nano /etc/crontab
```
@reboot root  /var/www/html/EVNotiPi/runs/atreboot.sh
*/1 * * * *   root   /var/www/html/EVNotiPi/runs/runs.sh
```

