""" Helper functions for watchdog modules """
from importlib import import_module

Modules = {
    'DUMMY': {'f': 'dummy', 'c': 'Dummy'},
    'GPIO': {'f': 'gpio', 'c': 'Gpio'},
    'I2C': {'f': 'i2c', 'c': 'I2C'},
}


def load(watchdog_type):
    """ Loader for watchdog modules. """
    if watchdog_type not in Modules.keys():
        raise ValueError('Unsupported watchdog %s' % (watchdog_type))

    return getattr(import_module("watchdog." + Modules[watchdog_type]['f']),
                   Modules[watchdog_type]['c'])
