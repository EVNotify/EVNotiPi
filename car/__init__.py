import os

def Load(car_type):
    if not "{}.py".format(car_type) in os.listdir('car'):
        raise Exception('Unsupported car {}'.format(car_type))

    exec("from car.{0} import {0} as CAR".format(car_type))

    return CAR
