""" Module for the Kia e-Niro """
from .kona_ev import KonaEv


class NiroEv(KonaEv):
    """ Class for the Kia e-Niro """

    def get_base_data(self):
        return {
            "CAPACITY": 64,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def get_evn_model(self):
        return 'NIRO_EV'