import os
from importlib import import_module

def Load(car_type):
    if not "{}.py".format(car_type) in os.listdir('car'):
        raise Exception('Unsupported car {}'.format(car_type))

    return getattr(import_module("car." + car_type), car_type)
