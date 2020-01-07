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

class NoData(Exception): pass

class EVNotify:
    def __init__(self, config, car):
        self.log = logging.getLogger("EVNotiPi/EVNotify")
        self.log.info("Initializing EVNotify")

        self.abortNotificationSent = False
        self.car = car
        self.chargingStartSOC = 0
        self.config = config
        self.last_charging = time()
        self.last_charging_soc = 0
        self.last_evn_settings_poll = 0
        self.notificationSent = False
        self.poll_interval = config['interval']
        self.running = False
        self.thread = None
        self.evnotify = evnotifyapi.EVNotify(config['akey'], config['token'])

        self.data = []
        self.gps_data = []
        self.data_lock = Condition()

        self.settings = None
        self.socThreshold = 100

        self.log.info("Get settings from backend")
        while self.settings == None:
            try:
                self.settings = self.evnotify.getSettings()
            except evnotifyapi.CommunicationError as e:
                self.log.info("Waiting for network connectivity")
                sleep(3)

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
        while self.running:
            with self.data_lock:
                self.log.debug('Waiting...')
                self.data_lock.wait()
                if len(self.data) == 0:
                    continue

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

            now = time()

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
                if is_charging:
                    self.last_charging = now
                    self.last_charging_soc = currentSOC

                if is_charging and 'socThreshold' not in self.config and \
                        now - self.last_evn_settings_poll > EVN_SETTINGS_INTERVAL:
                    try:
                        s = self.evnotify.getSettings()
                        # following only happens if getSettings is
                        # successful, else jumps into exception handler
                        self.settings = s
                        self.last_evn_settings_poll = now

                        if s['soc'] and s['soc'] != self.socThreshold:
                            self.socThreshold = int(s['soc'])
                            self.log.info("New notification threshold: {}".format(self.socThreshold))

                    except envotifyapi.CommunicationError as e:
                        self.log.error("Communication error occured",e)

                # track charging started
                if is_charging and self.chargingStartSOC == 0:
                    self.chargingStartSOC = currentSOC or 0
                # check if notification threshold reached
                #elif is_charging and chargingStartSOC < socThreshold and \
                #        currentSOC >= socThreshold and not notificationSent:
                #    print("Notification threshold reached")
                #    self.evnotify.sendNotification()
                #    notificationSent = True
                elif not is_connected:   # Rearm notification
                    self.chargingStartSOC = 0
                    self.notificationSent = False
                    self.abortNotificationSent = False

                if is_charging and \
                        self.last_charging_soc < self.socThreshold and \
                        currentSOC >= self.socThreshold:
                    self.evnotify.sendNotification()

            except evnotifyapi.CommunicationError as e:
                print(e)
            except NoData:
                pass

            # Detect aborted charge
            try:
                if not self.abortNotificationSent \
                        and now - self.last_charging > ABORT_NOTIFICATION_INTERVAL \
                        and self.chargingStartSOC > 0 and self.last_charging_soc < self.socThreshold:
                    self.log.info("No response detected, send abort notification")
                    self.evnotify.sendNotification(True)
                    self.abortNotificationSent = True

            except evnotifyapi.CommunicationError as e:
                self.log.error("Sending of notificatin failed! {}".format(e))


            # Prime next loop iteration
            if self.running:
                runtime = time() - now
                interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                if interval > 0:
                    sleep(interval)


    def checkWatchdog(self):
        return self.thread.is_alive()

