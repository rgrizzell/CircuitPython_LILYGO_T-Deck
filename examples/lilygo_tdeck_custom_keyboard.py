# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Robert Grizzell
#
# SPDX-License-Identifier: Unlicense
import time
import board
from lilygo_tdeck import Keyboard, TDeck


class MyCustomKeyboard(Keyboard):
    def __init__(self, backlight: bool = True):
        super().__init__(board.I2C())
        self.backlight(backlight)

    def backlight(self, state: bool = None, register: int = 0x1):
        """Send an I2C command to control the keyboard backlight.
        Custom keyboard firmware is required for this to work.
        """
        if state is None:
            buf = bytearray(1)
        else:
            buf = bytearray(2)
            buf[1] = int(state)
        buf[0] = register

        self._i2c.try_lock()
        self._i2c.writeto(self._i2c_addr, buffer=buf)
        self._i2c.unlock()


k = MyCustomKeyboard()
t = TDeck(keyboard=k)

while True:
    keypress = t.get_keypress()
    if keypress:
        print(keypress)
    time.sleep(0.1)
