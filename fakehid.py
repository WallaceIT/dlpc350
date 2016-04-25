"""
	This file is part of dlpc350 - A python library to control a DLPC350 DLP Digital Controller
    Copyright (C) 2016 Francesco Valla

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

class device:
    """Testing HID fake class"""

    def open(self, vendor_id=0, product_id=0, serial_number=None):
        return 1

    def write(self, buff):
        return 1

    def read(self, max_length, timeout_ms=0):
        return [0] * max_length

    def close(self):
        return 1

    def get_manufacturer_string(self):
        return "Francesco Valla"

    def get_product_string(self):
        return "FakeHID Device"

    def get_serial_number_string(self):
        return "0.1"
