""" Transmit data to EVNotify and handle notifications """
from time import time, sleep
from threading import Thread, Condition
import logging
import EVNotifyAPI

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

ARMED = 0
SENT = 1
FAILED = -1

class EVNotify:
    def __init__(self, config, car):
        self.log = logging.getLogger("EVNotiPi/EVNotify")
        self.log.info("Initializing EVNotify")

        self.car = car
        self.config = config
        self.poll_interval = config['interval']
        self.running = False
        self.thread = None

        self.data = []
        self.gps_data = []
        self.data_lock = Condition()

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
        log = self.log
        evn = EVNotifyAPI.EVNotify(self.config['akey'], self.config['token'])

        abort_notification = ARMED
        charging_start_soc = 0
        last_charging = time()
        last_charging_soc = 0
        last_evn_settings_poll = 0
        settings = None
        soc_notification = ARMED
        soc_threshold = self.config.get('soc_threshold', 100)

        log.info("Get settings from backend")
        while self.running and settings is None:
            try:
                settings = evn.getSettings()
            except EVNotifyAPI.CommunicationError as err:
                log.info("Waiting for network connectivity (%s)", err)
                sleep(3)

        while self.running:
            with self.data_lock:
                log.debug('Waiting...')
                self.data_lock.wait(max(10, self.poll_interval))
                now = time()

                # Detect aborted charge
                if ((now - last_charging > ABORT_NOTIFICATION_INTERVAL and
                     charging_start_soc > 0 and 0 < last_charging_soc < soc_threshold and
                     abort_notification is ARMED) or abort_notification is FAILED):
                    log.info("Aborted charge detected, send abort notification")
                    try:
                        evn.sendNotification(True)
                        abort_notification = SENT
                    except EVNotifyAPI.CommunicationError as err:
                        log.error("Communication Error: %s", err)
                        abort_notification = FAILED

                if len(self.data) == 0:
                    continue

                log.debug("Transmit...")

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
                evn.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])

                current_soc = data['SOC_DISPLAY'] or data['SOC_BMS']

                is_charging = True if data['charging'] else False
                is_connected = True if data['normalChargePort'] \
                        or data['rapidChargePort'] else False

                if data['fix_mode'] > 1:
                    location = {a:data[a] for a in ('latitude', 'longitude', 'speed')}
                    evn.setLocation({'location': location})

                extended_data = {a:data[a] for a in ExtendedFields if data[a] != None}
                log.debug(extended_data)
                evn.setExtended(extended_data)

            except EVNotifyAPI.CommunicationError as err:
                log.info("Communication Error: %s", err)

            # Notification handling from here on
            if is_charging and now - last_evn_settings_poll > EVN_SETTINGS_INTERVAL:
                try:
                    settings = evn.getSettings()
                    last_evn_settings_poll = now

                    if 'soc' in settings:
                        new_soc = int(settings['soc'])
                        if new_soc != socThreshold:
                            socThreshold = new_soc
                            log.info("New notification threshold: %i", socThreshold)

                except EVNotifyAPI.CommunicationError as err:
                    log.error("Communication error occured %s", err)

            # track charging started
            if is_charging and charging_start_soc == 0:
                charging_start_soc = current_soc or 0
            elif not is_connected:   # Rearm abort notification
                charging_start_soc = 0
                abort_notification = ARMED

            # SoC threshold notification
            if ((is_charging and 0 < last_charging_soc < soc_threshold <= current_soc)
                    or soc_notification is FAILED):
                log.info("Notification threshold(%i) reached: %i",
                         soc_threshold, current_soc)
                try:
                    evn.sendNotification()
                    soc_notification = ARMED
                except EVNotifyAPI.CommunicationError as err:
                    log.info("Communication Error: %s", err)
                    soc_notification = FAILED

            # Prime next loop iteration
            if self.running:
                runtime = time() - now
                interval = self.poll_interval - (runtime if runtime > self.poll_interval else 0)
                sleep(max(0, interval))


    def checkWatchdog(self):
        return self.thread.is_alive()

