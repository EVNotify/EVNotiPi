import os

def Load(dongle_type):
    if not "{}.py".format(dongle_type) in os.listdir('dongle'):
        raise Exception('Unsupported dongle {}'.format(dongle_type))

    exec("from dongle.{0} import {0} as DONGLE".format(dongle_type))

    return DONGLE
