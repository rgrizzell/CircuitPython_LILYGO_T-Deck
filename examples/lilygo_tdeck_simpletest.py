import time
from lilygo_tdeck import TDeck

t = TDeck()

while True:
    keypress = t.get_keypress()
    if keypress:
        print(keypress)
    time.sleep(0.1)
