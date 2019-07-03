from subprocess import check_call,check_output

class WiFiCtrl:
    def __init__(self):
        self.state = None
        self.enable()

    def enable(self):
        if self.state != True:
            check_call(['/bin/systemctl','start','hostapd'])
            self.state = True

    def disable(self):
        if self.state != False:
            if check_output(['/sbin/iw','dev','wlan0','station','dump','|','wc','-0'])  == b'':
                check_call(['/bin/systemctl','stop','hostapd'])
                self.state = False

