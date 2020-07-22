""" Helper functions for car modules """
from importlib import import_module

Modules = {
    'IONIQ_BEV': 'ioniq_bev',
    'IONIQ_FL_EV': 'ioniq_fl_ev',
    'KONA_EV': 'kona_ev',
    'NIRO_EV': 'niro_ev',
    'ZOE_Q210': 'zoe_q210',
    'ZOE_ZE50': 'zoe_ze50',
}


def load(car_type):
    """ Import a specific car module """
    if car_type not in Modules.keys():
        raise Exception('Unsupported car %s' % (car_type))

    return getattr(import_module("car." + Modules[car_type]), car_type)
