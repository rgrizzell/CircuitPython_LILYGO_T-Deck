# SPDX-FileCopyrightText: 2017 Scott Shawcroft, written for Adafruit Industries
# SPDX-FileCopyrightText: Copyright (c) 2023 Robert Grizzell
#
# SPDX-License-Identifier: MIT
"""
`lilygo_tdeck`
================================================================================

CircuitPython drivers for the LILYGO T-Deck peripherals.


* Author(s): Robert Grizzell

Implementation Notes
--------------------

**Hardware:**

* `LILYGO T-Deck <https://www.lilygo.cc/products/t-deck>`_

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads
"""
import sys
import audiobusio
import board
import storage
from countio import Counter

# from digitalio import DigitalInOut
from keypad import Event, Keys
from micropython import const
from sdcardio import SDCard

try:
    from busio import I2C
    from typing import Iterator
    from microcontroller import Pin
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/rgrizzell/CircuitPython_LILYGO_T-Deck.git"

_KEYBOARD_I2C_ADDR = const(0x55)
_MICROPHONE_I2C_ADDR = const(0x40)
_TOUCHSCREEN_I2C_ADDR = const(0x14)


class Keyboard:
    """Controls the keyboard peripheral. This class can be extended to support additional
    functionality if the keyboard is utilizing custom firmware.

    :param i2c: Object representing the I2C interface used to communicate with the keyboard.
    :type i2c: I2C
    :param int device_address: The I2C address of the keyboard device. Default is 0x55 (85).
    """

    def __init__(self, i2c: I2C, device_address: int = None) -> None:
        self._i2c = i2c
        self._i2c_addr = device_address or _KEYBOARD_I2C_ADDR

    def get_keypress(self) -> str | None:
        """Get the last keypress.

        :return: character representing the key that was pressed
        """
        buf = bytearray(1)
        self._i2c.try_lock()
        self._i2c.readfrom_into(self._i2c_addr, buffer=buf)
        self._i2c.unlock()

        if buf != b"\x00":
            return buf.decode()
        return None


# pylint: disable=too-many-arguments
class Trackball:
    """Controls the trackball peripheral.

    :param up_pin: Pin tracking upward movement from the trackball.
    :type up_pin: Pin
    :param Pin down_pin: Pin tracking downward movement from the trackball.
    :type down_pin: Pin
    :param Pin left_pin: Pin tracking leftward movement from the trackball.
    :type left_pin: Pin
    :param Pin right_pin: Pin tracking rightward movement from the trackball.
    :type right_pin: Pin
    :param Pin click_pin: Pin tracking presses on the trackball.
    :type click_pin: Pin
    """

    def __init__(
        self,
        up_pin: Pin,
        down_pin: Pin,
        left_pin: Pin,
        right_pin: Pin,
        click_pin: Pin = None,
    ) -> None:
        self.up = Counter(up_pin)  # pylint: disable=invalid-name
        self.right = Counter(right_pin)
        self.down = Counter(down_pin)
        self.left = Counter(left_pin)
        if click_pin:
            self.click = Keys([click_pin], value_when_pressed=False)

    def get_trackball(self) -> Iterator[tuple[str, int]]:
        """Get the last positional movement in units.

        :return: List of directions and the units of travel since last poll.
        """
        for direction in ["up", "right", "down", "left"]:
            counter = getattr(self, direction)
            yield direction, counter.count
            counter.reset()

    def get_click(self) -> Event:
        """Get the last click event.

        :return: Press or release event
        """
        event = self.click.events.get()
        return event


# pylint: disable=too-few-public-methods
class TDeck:
    """Class representing the LILYGO T-Deck.

    :param keyboard: Object representing the keyboard. If none is provided, one is created.
    :type keyboard: Keyboard
    :param trackball: Object representing the trackball. If none is provided, one is created.
    :type trackball: Trackball
    :param bool debug: Print extra debug statements during initialization.
    """

    def __init__(
        self,
        keyboard: Keyboard = None,
        trackball: Trackball = None,
        debug: bool = False,
    ) -> None:
        self.debug = debug
        if sys.implementation.version[0] < 9:
            raise NotImplementedError(
                "LILYGO T-Deck only supports CircuitPython version 9.0.0 or greater"
            )

        self._i2c = board.I2C()
        self._spi = board.SPI()

        # Touchscreen
        self._debug("Init touchscreen")
        # TODO: Create driver: https://github.com/rgrizzell/CircuitPython_GT911
        # int_pin = DigitalInOut(board.TOUCH_INT)
        # self.touchscreen = GT911(self._i2c, _TOUCHSCREEN_I2C_ADDR, int_pin=int_pin)

        # Keyboard
        self._debug("Init keyboard")
        self.keyboard = keyboard or Keyboard(self._i2c)
        self.get_keypress = self.keyboard.get_keypress

        # Trackball
        self._debug("Init Trackball")
        self.trackball = trackball or Trackball(
            board.TRACKBALL_UP,
            board.TRACKBALL_RIGHT,
            board.TRACKBALL_DOWN,
            board.TRACKBALL_LEFT,
            board.TRACKBALL_CLICK,
        )
        self.get_trackball = self.trackball.get_trackball
        self.get_click = self.trackball.get_click

        # SD Card
        self._debug("Init SD Card")
        self.sdcard = None
        try:
            self.sdcard = SDCard(self._spi, board.SDCARD_CS)
            vfs = storage.VfsFat(self.sdcard)
            storage.mount(vfs, "/sd")
        except OSError as error:
            print("SD Card disabled:", error)

        # Speaker
        self._debug("Init Speaker")
        self.speaker = None
        try:
            self.speaker = audiobusio.I2SOut(
                board.SPEAKER_SCK, board.SPEAKER_WS, board.SPEAKER_DOUT
            )
        except RuntimeError:
            pass

        # Microphone
        self._debug("Init Microphone")
        self.microphone = None
        if hasattr(audiobusio, "I2SIn"):
            self.microphone = audiobusio.I2SIn(
                board.MICROPHONE_SCK,
                board.MICROPHONE_WS,
                board.MICROPHONE_DIN,
                board.MICROPHONE_MCK,
            )
        else:
            print("Microphone disabled: audiobusio does not support I2S input")

        # LoRa - Optional
        # self._debug("Init LoRa")

    def _debug(self, msg):
        if self.debug:
            print(msg)
