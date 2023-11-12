import time
from lilygo_tdeck import TDeck

t = TDeck()

while True:
    print(t.get_keypress())
    time.sleep(0.1)
