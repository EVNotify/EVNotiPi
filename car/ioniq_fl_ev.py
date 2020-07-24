""" Module for Hyundai Ioniq Electric 38kWh """
from .kona_ev import KonaEv


class IoniqFlEv(KonaEv):
    """ Class for Hyundai Ioniq Electric 38kWh """

    def get_base_data(self):
        return {
            "CAPACITY": 38,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 4.6,
            "FAST_SPEED": 50.0
        }

    def get_abrp_model(self):
        return 'hyundai:ioniq:19:38:other'

    def get_evn_model(self):
        return 'IONIQ_FL_EV'
