""" Helper functions for dongle modules """
from importlib import import_module

Modules = {
    'ELM327': {'f': 'elm327', 'c': 'Elm327'},
    'PiOBD2Hat': {'f': 'pi_obd_hat', 'c': 'PiObd2Hat'},
    'SocketCAN': {'f': 'socket_can', 'c': 'SocketCan'},
    'FakeDongle': {'f': 'fake_dongle', 'c': 'FakeDongle'},
}


class CanError(Exception):
    """ CAN communication failed """


class NoData(Exception):
    """ CAN did not return any data in time """


def load(dongle_type):
    """ import a specific OBD2 module """
    if dongle_type not in Modules.keys():
        raise ValueError('Unsupported dongle %s' % (dongle_type))

    return getattr(import_module("dongle." + Modules[dongle_type]['f']),
                   Modules[dongle_type]['c'])
