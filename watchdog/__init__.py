""" Helper functions for watchdog modules """
import os
from importlib import import_module


def load(watchdog_type):
    """ Loader for watchdog modules. """
    if not "%s.py" % (watchdog_type) in os.listdir('watchdog'):
        raise Exception('Unsupported watchdog %s' % (watchdog_type))

    return getattr(import_module("watchdog." + watchdog_type), watchdog_type)
