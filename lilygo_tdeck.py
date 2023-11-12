"""
`lilygo_tdeck`

CircuitPython driver for LILYGO T-Deck.

* Author(s): Robert Grizzell

Implementation Notes
--------------------

**Hardware:**

* `LILYGO T-Deck <https://www.lilygo.cc/products/t-deck>`_

**Software and Dependencies**

* Adafruit CircuitPython firmware for the supported boards:
  https://github.com/adafruit/circuitpython/releases


| PIN | Board Label     | Description                             |
| --- | --------------- | --------------------------------------- |
| 0   | TRACKBALL_CLICK | Trackball Button Press (BOOT)           |
| 1   | TRACKBALL_LEFT  | Trackball Left                          |
| 2   | TRACKBALL_RIGHT | Trackball Right                         |
| 3   | TRACKBALL_UP    | Trackball Up                            |
| 4   | BAT_ADC         | Battery Input                           |
| 5   | SPEAKER_WS      | Speaker Word Select/Left-Right Clock    |
| 6   | SPEAKER_DOUT    | Speaker Serial Data                     |
| 7   | SPEAKER_SCK     | Speaker Serial Clock/Bit Clock          |
| 8   | SCL             | I2C Serial Clock                        |
| 9   | LORA_CS         | LoRa Chip Select                        |
| 10  | POWER_ON        | Power for peripherals (On by default)   |
| 11  | TFT_DC          | Display Commands                        |
| 12  | TFT_CS          | Display Chip Select                     |
| 13  | LORA_BUSY       | LoRa Busy                               |
| 14  | MICROPHONE_DIN  | Microphone Serial Data                  |
| 15  | TRACKBALL_DOWN  | Trackball Down                          |
| 16  | TOUCH_INT       | Touchscreen Interrupt                   |
| 17  | LORA_RST        | LoRa Reset                              |
| 18  | SDA             | I2C Serial Data                         |
| 19  | N/A             | USB DM/D- (ESP32 Only)                  |
| 20  | N/A             | USB DP/D+ (ESP32 Only)                  |
| 21  | MICROPHONE_WS   | Microphone Word Select/Left-Right Clock |
| 35  | N/A             | Unused                                  |
| 36  | N/A             | Unused                                  |
| 37  | N/A             | Unused                                  |
| 38  | MISO            | SPI Main In Sub Out                     |
| 39  | SDCARD_CS       | SD Card Chip Select                     |
| 40  | CLK             | SPI Serial Clock                        |
| 41  | MOSI            | SPI Main Out Sub In                     |
| 42  | TFT_BKLT        | Display Backlight                       |
| 43  | TX              | UART Transmit                           |
| 44  | RX              | UART Receive                            |
| 45  | LORA_DIO1       | LoRa Interrupt                          |
| 46  | KEYBOARD_INT    | Keyboard Interrupt                      |
| 47  | MICROPHONE_SCK  | Microphone Serial Clock                 |
| 48  | MICROPHONE_MCK  | Microphone Master Clock                 |
| N/A | UART            | Returns UART Object                     |
| N/A | SPI             | Returns SPI Object                      |
| N/A | I2C             | Returns I2C Object                      |
| N/A | DISPLAY         | Returns Display Object                  |

"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/rgrizzell/LILYGO_T_Deck_CircuitPython.git"

import audiobusio
import board
import countio
import gc
import keypad
import microcontroller
import sdcardio
import storage
import sys

try:
    from typing import Iterator
except ImportError:
    pass


class TDeck:
    """Class representing the LILYGO T-Deck.

    :param bool keyboard_backlight: Set to `True` to turn on the keyboard backlight.
    :param int keyboard_i2c_address: The I2C address of the keyboard. Default: 0x55
    :param bool debug: Print extra debug statements during initialization.
    """
    def __init__(
        self,
        keyboard_backlight: bool = False,
        keyboard_i2c_address: int = 0x55,
        debug: bool = False
    ) -> None:
        self.debug = debug
        if sys.implementation.version[0] < 9:
            raise NotImplementedError("LILYGO T-Deck only supports CircuitPython version 9.0.0 or greater")

        self._i2c = board.I2C()
        self._spi = board.SPI()

        # Keyboard
        self._debug("Init keyboard")
        self.keyboard = keyboard_i2c_address
        if keyboard_backlight:
            self._debug("Turn on keyboard backlight")
            buf = bytearray(b'1')
            self._i2c.try_lock()
            self._i2c.writeto_then_readfrom(self.keyboard, out_buffer=buf, in_buffer=buf)
            self._i2c.unlock()
            if buf != b'1':
                print("Can not turn on backlight. Please upgrade your keyboard firmware.")

        # Trackball
        self._debug("Init Trackball")
        self.trackball = Trackball(
            board.TRACKBALL_UP,
            board.TRACKBALL_RIGHT,
            board.TRACKBALL_DOWN,
            board.TRACKBALL_LEFT,
            board.TRACKBALL_CLICK
        )

        # SD Card
        self._debug("Init SD Card")
        self.sdcard = None
        try:
            self.sdcard = sdcardio.SDCard(self._spi, board.SDCARD_CS)
            vfs = storage.VfsFat(self.sdcard)
            storage.mount(vfs, "/sd")
        except OSError as error:
            print("SD Card disabled:", error)

        # Speaker
        self._debug("Init Speaker")
        self.speaker = None
        try:
            self.speaker = audiobusio.I2SOut(
                board.SPEAKER_SCK,
                board.SPEAKER_WS,
                board.SPEAKER_DOUT
            )
        except RuntimeError:
            pass

        # Microphone
        self._debug("Init Microphone")
        self.microphone = None
        if hasattr(audiobusio, 'I2SIn'):
            self.microphone = audiobusio.I2SIn(
                board.MICROPHONE_SCK,
                board.MICROPHONE_WS,
                board.MICROPHONE_DIN,
                board.MICROPHONE_MCK
            )
        else:
            print("Microphone disabled: audiobusio does not support I2S input")

        # LoRa - Optional
        # self._debug("Init LoRa")

        gc.collect()

    def get_keypress(self) -> str:
        r = bytearray(1)
        self._i2c.try_lock()
        self._i2c.readfrom_into(self.keyboard, r)
        self._i2c.unlock()
        if r != b'\x00':
            return r.decode()

    def _debug(self, msg):
        if self.debug:
            print(msg)


class Trackball:
    """ Controls the trackball peripheral. """
    def __init__(
        self,
        up: microcontroller.Pin,
        down: microcontroller.Pin,
        left: microcontroller.Pin,
        right: microcontroller.Pin,
        click: microcontroller.Pin = None
    ):
        self.up = countio.Counter(up)
        self.right = countio.Counter(right)
        self.down = countio.Counter(down)
        self.left = countio.Counter(left)
        if click:
            self.click = keypad.Keys([click], value_when_pressed=False)

    def get_trackball(self) -> Iterator[tuple[str, int]]:
        for d in ["up", "right", "down", "left"]:
            c = getattr(self, d)
            yield d, c.count
            c.reset()
