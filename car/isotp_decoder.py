""" Generic decoder for ISO-TP based cars """
import logging
import struct
from dongle import NoData

FormatMap = {
    0: {'f': 'x'},
    1: {'f': 'b'},
    2: {'f': 'h'},
    3: {'f': 'bh', 'l': lambda o: o[0] << 16 | o[1]},
    4: {'f': 'i'},
    8: {'f': 'l'},
}


def is_power_of_two(number):
    """ Check of argument has power of two """
    return (number & (number-1) == 0) and number != 0


class IsoTpDecoder:
    """ Generic decoder for ISO-TP based cars """

    def __init__(self, dongle, fields):
        self._log = logging.getLogger("EVNotiPi/ISO-TP-Decoder")
        self._dongle = dongle
        self._fields = fields

        self.preprocess_fields()

    def preprocess_fields(self):
        """ Preprocess field structure, creating format strings for unpack etc.,"""
        for cmd_data in self._fields:
            fmt = ">"
            fmt_idx = 0

            # make sure 'computed' is set so we don't need to check for it
            # in the decoder. Checking is slow.
            cmd_data['computed'] = cmd_data.get('computed', False)

            if not cmd_data['computed']:
                # Build a new array instead of inserting into the existing one.
                # Should be quicker.
                new_fields = []
                for field in cmd_data['fields']:
                    self._log.debug(field)
                    # Non power of two types are hard as is. For now those can
                    # not be used in patterned fields.
                    if field.get('cnt', 1) > 1 and not is_power_of_two(field['width']):
                        raise ValueError('Non power of two field in patterned field not allowed')

                    if not field.get('width', 0) in FormatMap.keys():
                        raise ValueError('Unsupported field length')

                    if field.get('padding', 0) > 0:
                        field_fmt = str(field.get('padding')) + 'x'
                        self._log.debug("field_fmt(%s)", field_fmt)
                        fmt += field_fmt
                    elif not field.get('computed', False):
                        # For patterned fields (i.e. cellVolts%02d) use multiplyer
                        # in format string.
                        field_fmt = str(field.get('cnt', ''))
                        if field.get('signed', False):
                            field_fmt += FormatMap[field['width']]['f'].lower()
                        else:
                            field_fmt += FormatMap[field['width']]['f'].upper()

                        self._log.debug("field_fmt(%s)", field_fmt)
                        fmt += field_fmt

                        if not is_power_of_two(field['width']):
                            if 'lanbda' in field:
                                self._log.warning('defining lambda on non power ow two length fields may give unexpected results!')
                            else:
                                field['lambda'] = FormatMap[field['width']]['l']

                        field['scale'] = field.get('scale', 1)
                        field['offset'] = field.get('offset', 0)

                        if 'name' not in field:
                            raise ValueError('Name missing in Field')

                        start = field.get('idx', 0)
                        cnt = field.get('cnt', 1)

                        for field_idx in range(start, start + cnt):
                            # Expand patterned fields into simple fields to
                            # match the format string. Append new field to the
                            # array of new fields. We need to copy the existing
                            # field, else all field names will reference the same
                            # string
                            new_field = field.copy()
                            if cnt > 1:
                                new_field['name'] %= field_idx

                            new_field['fmt_idx'] = fmt_idx
                            new_field['fmt_len'] = len(FormatMap[field['width']])
                            fmt_idx += new_field['fmt_len']

                            new_fields.append(new_field)

                self._log.debug("fmt(%s)", fmt)
                cmd_data['struct'] = struct.Struct(fmt)
                cmd_data['fields'] = new_fields

    def get_data(self):
        """ Takes a structure which describes adresses,
            commands and how to decode the return """
        data = {}
        for cmd_data in self._fields:
            try:
                if cmd_data['computed']:
                    # Fields of computed "commands" are filled by executing
                    # the fields lambda with the data dict as argument
                    for field in cmd_data['fields']:
                        name = field['name']
                        func = field['lambda']
                        data[name] = func(data)
                else:
                    # Send a command to the CAN bus and parse the resulting
                    # bytearray using unpack. The format for unpack was generated
                    # in the preprocessor. Extracted values are scaled, shifted
                    # and a lambda function is executed if provided
                    raw = self._dongle.send_command_ex(cmd_data['cmd'],
                                                       canrx=cmd_data['canrx'],
                                                       cantx=cmd_data['cantx'])
                    raw_fields = cmd_data['struct'].unpack(raw)

                    for field in cmd_data['fields']:
                        name = field['name']
                        fmt_idx = field['fmt_idx']
                        fmt_len = field['fmt_len']

                        if 'lambda' in field:
                            value = field['lambda'](raw_fields[fmt_idx:fmt_idx+fmt_len])
                        else:
                            value = raw_fields[fmt_idx]

                        data[name] = value * field['scale'] + field['offset']

            except NoData:
                if not cmd_data.get('optional', False):
                    raise
            except struct.error as err:
                self._log.error("err(%s) cmd(%s) fmt(%s):%d raw(%s):%d", err, cmd_data['cmd'].hex(),
                                cmd_data['cmd_format'], struct.calcsize(cmd_data['cmd_format']),
                                raw.hex(), len(raw))
                raise

        return data
