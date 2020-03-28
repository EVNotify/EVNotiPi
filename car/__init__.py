
def Load(car_name):

    exec("from .{0} import {0} as CAR".format(config['car']['type']))
