from subprocess import check_call

class WiFiCtrl:
    def __init__(self):
        self.state = None
        self.enable()

    def enable(self):
        if self.state != True:
            check_call(['/usr/bin/systemctl','start','hostapd'])
            self.state = True

    def disable(self):
        if self.state != False:
            check_call(['/usr/bin/systemctl','stop','hostapd'])
            self.state = False

