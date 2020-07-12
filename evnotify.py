import evnotifyapi
from time import time, sleep
from threading import Thread, Condition
import logging

EVN_SETTINGS_INTERVAL = 300
ABORT_NOTIFICATION_INTERVAL = 60

ExtendedFields = (
        'auxBatteryVoltage',
        'batteryInletTemperature',
        'batteryMaxTemperature',
        'batteryMinTemperature',
        'cumulativeEnergyCharged',
        'cumulativeEnergyDischarged',
        'charging',
        'normalChargePort',
        'rapidChargePort',
        'dcBatteryCurrent',
        'dcBatteryPower',
        'dcBatteryVoltage',
        'soh',
        'externalTemperature'
        )

class EVNotify:
    def __init__(self, config, car):
        self.log = logging.getLogger("EVNotiPi/EVNotify")
        self.log.info("Initializing EVNotify")

        self.abortNotificationFailed = False
        self.car = car
        self.chargingStartSOC = 0
        self.last_charging = time()
        self.config = config
        self.last_charging_soc = 0
        self.last_evn_settings_poll = 0
        self.notificationFailed = False
        self.poll_interval = config['interval']
        self.running = False
        self.thread = None
        self.evnotify = evnotifyapi.EVNotify(config['akey'], config['token'])

        self.data = []
        self.gps_data = []
        self.data_lock = Condition()

        self.settings = None
        self.socThreshold = self.config['soc_threshold'] or 100

    def start(self):
        self.running = True
        self.thread = Thread(target = self.submitData, name = "EVNotiPi/EVNotify")
        self.thread.start()
        self.car.registerData(self.dataCallback)

    def stop(self):
        self.car.unregisterData(self.dataCallback)
        self.running = False
        with self.data_lock:
            self.data_lock.notify()
        self.thread.join()

    def dataCallback(self, data):
        self.log.debug("Enqeue...")
        with self.data_lock:
            self.data.append(data)
            self.data_lock.notify()

    def submitData(self):
        self.log.info("Get settings from backend")
        while self.settings == None:
            try:
                self.settings = self.evnotify.getSettings()
            except evnotifyapi.CommunicationError as e:
                self.log.info("Waiting for network connectivity")
                sleep(3)

        while self.running:
            with self.data_lock:
                self.log.debug('Waiting...')
                self.data_lock.wait()
                if len(self.data) == 0:
                    continue

                now = time()

                self.log.debug("Transmit...")

                avgs = {
                        'dcBatteryCurrent': [],
                        'dcBatteryPower': [],
                        'dcBatteryVoltage': [],
                        'speed': [],
                        'latitude': [],
                        'longitude': [],
                        'altitude': [],
                        }

                for d in self.data:
                    for k,v in avgs.items():
                        if k in d and d[k] != None:
                            v.append(d[k])

                # Need to copy data here because we update it later
                data = self.data[-1].copy()
                self.data.clear()

            data.update({k:sum(v)/len(v) for k,v in avgs.items() if len(v) > 0})


            try:
                self.last_data = now

                self.evnotify.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])

                currentSOC = data['SOC_DISPLAY'] or data['SOC_BMS']

                is_charging = True if data['charging'] else False
                is_connected = True if data['normalChargePort'] \
                        or data['rapidChargePort'] else False

                if data['fix_mode'] > 1:
                    location = {a:data[a] for a in ('latitude', 'longitude', 'speed')}
                    self.evnotify.setLocation({'location': location})

                extended_data = {a:data[a] for a in ExtendedFields if data[a] != None}
                self.log.debug(extended_data)
                self.evnotify.setExtended(extended_data)

                # Notification handling from here on
                if is_charging and now - self.last_evn_settings_poll > EVN_SETTINGS_INTERVAL:

                    try:
                        s = self.evnotify.getSettings()
                        # following only happens if getSettings is
                        # successful, else jumps into exception handler
                        self.settings = s
                        self.last_evn_settings_poll = now

                        if s['soc'] and s['soc'] != self.socThreshold:
                            self.socThreshold = int(s['soc'])
                            self.log.info("New notification threshold: %i", self.socThreshold)

                    except evnotifyapi.CommunicationError as e:
                        self.log.error("Communication error occured %s", e)

                # track charging started
                if is_charging and self.chargingStartSOC == 0:
                    self.chargingStartSOC = currentSOC or 0
                elif not is_connected:   # Rearm notification
                    self.chargingStartSOC = 0
                    self.notificationFailed = False
                
                # soc threshold notification
                if ((is_charging and self.last_charging_soc < self.socThreshold <= currentSOC) or self.notificationFailed):
                    try:
                        self.evnotify.sendNotification()
                        self.notificationFailed = False
                    except evnotifyapi.CommunicationError as e:
                        self.log.error("Communication error occured %s", e)
                        self.notificationFailed = True
                        
                # Detect aborted charge
                if ((now - self.last_charging > ABORT_NOTIFICATION_INTERVAL and self.chargingStartSOC > 0 and self.last_charging_soc < self.socThreshold) or self.abortNotificationFailed):
                    self.log.info("Aborted charge detected, send abort notification")
                    try:
                        self.evnotify.sendNotification(True)
                        self.abortNotificationFailed = False
                    except evnotifyapi.CommunicationError as e:
                        self.log.error("Communication error occured %s", e)
                        self.abortNotificationFailed = True
                        
                if is_charging:
                    self.last_charging = now
                    self.last_charging_soc = currentSOC
                    
                # Prime next loop iteration
                if self.running:
                    runtime = time() - now
                    interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                    sleep(min(0, interval))

            except evnotifyapi.CommunicationError as e:
                self.log.error("Communication error occured %s", e)


    def checkWatchdog(self):
        return self.thread.is_alive()

