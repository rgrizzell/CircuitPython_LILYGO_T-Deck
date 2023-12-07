# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Robert Grizzell
#
# SPDX-License-Identifier: Unlicense
import time
from lilygo_tdeck import TDeck

t = TDeck()

while True:
    keypress = t.get_keypress()
    if keypress:
        print(keypress)

    click = t.get_click()
    if click:
        print(click)

    for p, c in t.get_trackball():
        if c > 0:
            print(f"{p}: {c}")

    time.sleep(0.1)
