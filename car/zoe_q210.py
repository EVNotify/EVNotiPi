""" Module for the Zoe Q210 """
from .zoe import Zoe


class ZoeQ210(Zoe):
    """ Class for the Zoe Q210 """

    def get_base_data(self):
        return {
            "CAPACITY": 22,
            "SLOW_SPEED": 2.3,
            "NORMAL_SPEED": 22.0,
            "FAST_SPEED": 43.0
        }

    def get_abrp_model(self):
        return 'renault:zoe:q210:22:other'

    def get_evn_model(self):
        return 'ZOE_Q210'
