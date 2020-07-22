""" Helper functions for dongle modules """
from importlib import import_module

Modules = {
    'ELM327': 'elm327',
    'PiOBD2Hat': 'pi_obd_hat',
    'SocketCAN': 'socket_can',
    'FakeDongle': 'fake_dongle',
}


class CanError(Exception):
    """ CAN communication failed """


class NoData(Exception):
    """ CAN did not return any data in time """


def load(dongle_type):
    """ import a specific OBD2 module """
    if dongle_type not in Modules.keys():
        raise Exception('Unsupported dongle %s' % (dongle_type))

    return getattr(import_module("dongle." + Modules[dongle_type]), dongle_type)
