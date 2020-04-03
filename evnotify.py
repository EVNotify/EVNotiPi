from time import time, sleep
from threading import Thread, Condition
import logging
import EVNotifyAPI

EVN_SETTINGS_INTERVAL = 300
ABORT_NOTIFICATION_INTERVAL = 60

EXTENDED_FIELDS = (
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
        'externalTemperature',
        'odo'
        )

ARMED = 0
SENT = 1
FAILED = -1

class EVNotify:
    def __init__(self, config, car):
        self._log = logging.getLogger("EVNotiPi/EVNotify")
        self._log.info("Initializing EVNotify")

        self._car = car
        self.config = config
        self._poll_interval = config['interval']
        self._running = False
        self._thread = None
        self._evnotify = EVNotifyAPI.EVNotify(config['akey'], config['token'])

        self._data = []
        self._gps_data = []
        self._data_lock = Condition()

    def start(self):
        self._running = True
        self._thread = Thread(target=self.submitData, name="EVNotiPi/EVNotify")
        self._thread.start()
        self._car.registerData(self.dataCallback)

    def stop(self):
        self._car.unregisterData(self.dataCallback)
        self._running = False
        with self._data_lock:
            self._data_lock.notify()
        self._thread.join()

    def dataCallback(self, data):
        self._log.debug("Enqeue...")
        with self._data_lock:
            if data['SOC_DISPLAY'] is not None:
                self._data.append(data)
                self._data_lock.notify()

    def submitData(self):
        log = self._log
        evn = self._evnotify

        abort_notification = ARMED
        charging_start_soc = 0
        last_charging = time()
        last_charging_soc = 0
        last_evn_settings_poll = 0
        settings = None
        soc_notification = ARMED
        soc_threshold = self.config.get('soc_threshold', 100)

        log.info("Get settings from backend")
        while settings is None:
            try:
                settings = evn.getSettings()
            except EVNotifyAPI.CommunicationError as e:
                log.info("Waiting for network connectivity")
                sleep(3)

        while self._running:
            with self._data_lock:
                log.debug('Waiting...')
                self._data_lock.wait(max(10, self._poll_interval))
                now = time()

                # Detect aborted charge
                if ((now - last_charging > ABORT_NOTIFICATION_INTERVAL and
                     charging_start_soc > 0 and 0 < last_charging_soc < soc_threshold and
                     abort_notification is ARMED) or abort_notification is FAILED):
                    log.info("Aborted charge detected, send abort notification")
                    try:
                        evn.sendNotification(True)
                        abort_notification = SENT
                    except EVNotifyAPI.CommunicationError as e:
                        log.error("Communication Error: %s", e)
                        abort_notification = FAILED

                if len(self._data) == 0:
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

                for d in self._data:
                    for k, v in avgs.items():
                        if k in d and d[k] is not None:
                            v.append(d[k])

                # Need to copy data here because we update it later
                data = self._data[-1].copy()
                self._data.clear()

            data.update({k:sum(v)/len(v) for k, v in avgs.items() if len(v) > 0})

            try:
                evn.setSOC(data['SOC_DISPLAY'], data['SOC_BMS'])

                current_soc = data['SOC_DISPLAY'] or data['SOC_BMS']

                is_charging = bool(data['charging'])
                is_connected = bool(data['normalChargePort'] \
                        or data['rapidChargePort'])

                if data['fix_mode'] > 1:
                    location = {a:data[a] for a in ('latitude', 'longitude', 'speed')}
                    evn.setLocation({'location': location})

                extended_data = {a:data[a] for a in EXTENDED_FIELDS if data[a] is not None}
                log.debug(extended_data)
                evn.setExtended(extended_data)

            except EVNotifyAPI.CommunicationError as e:
                log.info("Communication Error: %s", e)

            # Notification handling from here on
            if is_charging and now - last_evn_settings_poll > EVN_SETTINGS_INTERVAL:
                try:
                    settings = evn.getSettings()
                    last_evn_settings_poll = now

                    if settings['soc'] and settings['soc'] != soc_threshold:
                        soc_threshold = int(settings['soc'])
                        log.info("New notification threshold: %s",
                                 soc_threshold)

                except EVNotifyAPI.CommunicationError as e:
                    log.error("Communication error occured %s", e)

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
                except EVNotifyAPI.CommunicationError as e:
                    log.info("Communication Error: %s", e)
                    soc_notification = FAILED

            if is_charging:
                last_charging = now
                last_charging_soc = current_soc


            # Prime next loop iteration
            if self._running:
                runtime = time() - now
                interval = self._poll_interval - (runtime if runtime > self._poll_interval else 0)
                sleep(max(0, interval))


    def checkWatchdog(self):
        return self._thread.is_alive()
