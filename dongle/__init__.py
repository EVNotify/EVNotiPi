""" Helper functions for dongle modules """
import os
from importlib import import_module

def load(dongle_type):
    """ import a specific OBD2 module """
    if not "%s.py" % (dongle_type) in os.listdir('dongle'):
        raise Exception('Unsupported dongle %s' % (dongle_type))

    return getattr(import_module("dongle." + dongle_type), dongle_type)
