""" Helper functions for car modules """
import os
from importlib import import_module

def load(car_type):
    """ Import a specific car module """
    if not "%s.py" % (car_type) in os.listdir('car'):
        raise Exception('Unsupported car %s' % (car_type))

    return getattr(import_module("car." + car_type), car_type)
