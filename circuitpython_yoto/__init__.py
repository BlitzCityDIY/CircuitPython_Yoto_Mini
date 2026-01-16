# SPDX-FileCopyrightText: 2026 Your Name
# SPDX-License-Identifier: MIT

"""
`circuitpython_yoto`
================================================================================

Helper library for the Yoto Mini music player running CircuitPython


* Author(s): Your Name

Implementation Notes
--------------------

**Hardware:**

* Yoto Mini Music Player (reverse engineered)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Required Libraries:
  - adafruit_bus_device
  - adafruit_register
  - adafruit_pcf8563

"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/yourrepo/CircuitPython_Yoto_Mini.git"

# Import the main helper class and convenience function
from .yoto_mini import YotoMini

from .cr95hf import CR95HF
from .es8156 import ES8156
from .sgm41513 import SGM41513
from .tcal6416 import TCAL6416

# Make the main classes available at package level
__all__ = [
    'YotoMini',
    'CR95HF',
    'ES8156',
    'SGM41513',
    'TCAL6416',
]