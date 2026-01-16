# SPDX-FileCopyrightText: 2026 Your Name
# SPDX-License-Identifier: MIT

"""
`yoto_mini`
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

"""

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/yourrepo/CircuitPython_Yoto_Mini.git"

import time
import board
import busio
import audiobusio
import rotaryio
from digitalio import DigitalInOut, Direction, Pull

# Import all the peripheral drivers (relative imports for package)
from .cr95hf import CR95HF
from .es8156 import ES8156
from .sgm41513 import SGM41513
from .tcal6416 import TCAL6416
from adafruit_pcf8563.pcf8563 import PCF8563


class YotoMini:
    """
    Helper class for the Yoto Mini music player.
    
    Provides easy access to all onboard peripherals:
    - NFC/RFID reader (CR95HF)
    - I2S DAC (ES8156) 
    - Battery charger (SGM41513)
    - RTC (PCF8563)
    - Two rotary encoders with buttons
    - IO Expander (TCAL6416)
    
    :param bool init_nfc: Initialize the NFC reader. Defaults to True.
    :param bool init_audio: Initialize the audio DAC and I2S. Defaults to True.
    :param bool init_battery: Initialize the battery charger interface. Defaults to True.
    :param bool init_rtc: Initialize the RTC. Defaults to True.
    :param bool init_encoders: Initialize the rotary encoders. Defaults to True.
    :param int audio_sample_rate: Audio sample rate in Hz. Defaults to 44100.
    :param int audio_bit_depth: Audio bit depth (8 or 16). Defaults to 16.
    :param bool use_sclk_as_mclk: Use SCLK as MCLK for ES8156. Defaults to True.
    """
    
    def __init__(
        self,
        *,
        init_nfc=True,
        init_audio=True, 
        init_battery=True,
        init_rtc=True,
        init_encoders=True,
        audio_sample_rate=44100,
        audio_bit_depth=16,
        use_sclk_as_mclk=True,
    ):
        
        # Initialize I2C bus (shared by multiple peripherals)
        self._i2c = board.I2C()
        
        # Initialize IO Expander first (needed for encoder buttons)
        self.io_expander = TCAL6416(self._i2c, address=0x20)
        self.io_expander.configure_yoto_mini_defaults()
        
        # Initialize NFC reader
        self._nfc = None
        if init_nfc:
            try:
                uart = busio.UART(
                    board.D32,  # TX
                    board.D33,  # RX
                    baudrate=57600,
                    bits=8,
                    stop=2,
                    timeout=0.1
                )
                self._nfc = CR95HF(uart)
            except Exception as e:
                raise(f"    ✗ NFC initialization failed: {e}")
        
        # Initialize audio DAC and I2S
        self._audio = None
        self._dac = None
        if init_audio:
            try:
                self._dac = ES8156(self._i2c, address=0x08)
                
                # Configure DAC
                self._dac.configure(use_sclk_as_mclk=False)
                
                # Initialize I2S
                self._audio = audiobusio.I2SOut(
                    board.D5,   # I2S_BCLK
                    board.D18,  # I2S_WS
                    board.D19,   # I2S_DIN
                    main_clock=board.D0    # I2S_MCLK
                )
                
                # Set default volume
                self._dac.volume = 150
                self._dac.mute = False
            except Exception as e:
                raise RuntimeError(f"Audio initialization failed: {e}")
        
        # Initialize battery charger
        self._battery = None
        if init_battery:
            try:
                self._battery = SGM41513(self._i2c, address=0x1A)
                part = self._battery.part_info
            except Exception as e:
                raise RuntimeError(f"Battery charger initialization failed: {e}")
        
        # Initialize RTC
        self._rtc = None
        if init_rtc:
            try:
                self._rtc = PCF8563(self._i2c)
                if not self._rtc.datetime_compromised:
                    current_time = self._rtc.datetime
            except Exception as e:
                raise RuntimeError(f"RTC initialization failed: {e}")
        
        # Initialize rotary encoders
        self._encoder_left = None
        self._encoder_right = None
        self._encoder_left_button_pin = 5  # P0_5 on IO expander
        self._encoder_right_button_pin = 4  # P0_4 on IO expander
        
        if init_encoders:
            try:
                # Encoder 1: A=D39, B=D35
                self._encoder_left = rotaryio.IncrementalEncoder(board.D39, board.D35)
                self._encoder_left_last_position = self._encoder_left.position
                
                # Encoder 2: A=D36, B=D27  
                self._encoder_right = rotaryio.IncrementalEncoder(board.D36, board.D27)
                self._encoder_right_last_position = self._encoder_right.position
            except Exception as e:
                raise RuntimeError(f"Encoder initialization failed: {e}")
    
    # NFC/RFID Properties and Methods
    @property
    def nfc(self):
        """Access the CR95HF NFC reader directly"""
        return self._nfc
    
    def read_nfc_tag(self):
        """
        Read an NFC tag if present.
        
        :return: Tuple of (uid_bytes, sak_byte) or (None, None) if no tag present
        """
        if self._nfc is None:
            return None, None
        return self._nfc.read_tag()
    
    def get_card_type(self, sak):
        """
        Get the card type description from SAK byte.
        
        :param int sak: SAK byte from read_nfc_tag()
        :return: String description of card type
        """
        if self._nfc is None:
            return "NFC not initialized"
        return self._nfc.card_type(sak)
    
    # Audio Properties and Methods
    @property
    def audio(self):
        """Access the I2SOut audio interface directly"""
        return self._audio
    
    @property
    def dac(self):
        """Access the ES8156 DAC directly"""
        return self._dac
    
    @property
    def volume(self):
        """Get/set the audio volume (0-255)"""
        if self._dac is None:
            return 0
        return self._dac.volume
    
    @volume.setter
    def volume(self, value):
        if self._dac is not None:
            self._dac.volume = max(0, min(255, value))
    
    @property
    def mute(self):
        """Get/set the mute state (True=muted, False=unmuted)"""
        if self._dac is None:
            return True
        return self._dac.mute
    
    @mute.setter
    def mute(self, value):
        if self._dac is not None:
            self._dac.mute = value
    
    def play(self, audio_sample, loop=False):
        """
        Play an audio sample.
        
        :param audio_sample: An audiocore.RawSample or audiocore.WaveFile
        :param bool loop: Whether to loop the audio
        """
        if self._audio is not None:
            self._audio.play(audio_sample, loop=loop)
    
    def stop(self):
        """Stop audio playback"""
        if self._audio is not None:
            self._audio.stop()
    
    @property
    def playing(self):
        """Whether audio is currently playing"""
        if self._audio is None:
            return False
        return self._audio.playing
    
    # Battery Properties and Methods
    @property
    def battery(self):
        """Access the SGM41513 battery charger directly"""
        return self._battery
    
    @property
    def charge_status(self):
        """
        Get current battery and charging status.
        
        :return: Dictionary with status information or None if not initialized
        """
        if self._battery is None:
            return None
        return self._battery.system_status
    
    @property
    def charge_voltage(self):
        """Get the charge voltage setting in mV"""
        if self._battery is None:
            return None
        return self._battery.charge_voltage
    
    @property
    def charge_current(self):
        """Get the charge current setting in mA"""
        if self._battery is None:
            return None
        return self._battery.charge_current
    
    @property
    def charging(self):
        """Whether the battery is currently charging"""
        if self._battery is None:
            return False
        status = self._battery.system_status
        return status['charge_stat_code'] in (1, 2)  # Pre-charge or Fast Charge
    
    @property
    def charge_complete(self):
        """Whether charging is complete"""
        if self._battery is None:
            return False
        status = self._battery.system_status
        return status['charge_stat_code'] == 3  # Complete

    @property
    def rtc(self):
        """Access the PCF8563 RTC directly"""
        return self._rtc
    
    @property
    def datetime(self):
        """Get/set the RTC datetime as time.struct_time"""
        if self._rtc is None:
            return None
        return self._rtc.datetime
    
    @datetime.setter
    def datetime(self, value):
        if self._rtc is not None:
            self._rtc.datetime = value
    
    @property
    def rtc_valid(self):
        """Whether the RTC has valid time (not compromised)"""
        if self._rtc is None:
            return False
        return not self._rtc.datetime_compromised
    
    # Encoder Properties and Methods
    @property
    def encoder_left(self):
        """Access encoder 1 directly"""
        return self._encoder_left
    
    @property
    def encoder_right(self):
        """Access encoder 2 directly"""
        return self._encoder_right
    
    @property
    def encoder_left_position(self):
        """Get the current position of encoder 1"""
        if self._encoder_left is None:
            return 0
        return self._encoder_left.position
    
    @property
    def encoder_right_position(self):
        """Get the current position of encoder 2"""
        if self._encoder_right is None:
            return 0
        return self._encoder_right.position
    
    def encoder_left_delta(self):
        """
        Get the change in encoder 1 position since last call.
        
        :return: Integer change in position (positive=clockwise, negative=counter-clockwise)
        """
        if self._encoder_left is None:
            return 0
        current = self._encoder_left.position
        delta = current - self._encoder_left_last_position
        self._encoder_left_last_position = current
        return delta
    
    def encoder_right_delta(self):
        """
        Get the change in encoder 2 position since last call.
        
        :return: Integer change in position (positive=clockwise, negative=counter-clockwise)
        """
        if self._encoder_right is None:
            return 0
        current = self._encoder_right.position
        delta = current - self._encoder_right_last_position
        self._encoder_right_last_position = current
        return delta
    
    @property
    def encoder_left_button(self):
        """Whether encoder 1 button is pressed (True=pressed)"""
        return self.io_expander.get_pin(self._encoder_left_button_pin)
    
    @property
    def encoder_right_button(self):
        """Whether encoder 2 button is pressed (True=pressed)"""
        return self.io_expander.get_pin(self._encoder_right_button_pin)
    
    def deinit(self):
        """Deinitialize all peripherals and release hardware resources"""
        if self._audio is not None:
            self._audio.stop()
            self._audio.deinit()
        
        if self._dac is not None:
            self._dac.mute = True
        
        if self._nfc is not None:
            self._nfc.field_off()
        
        if self._encoder_left is not None:
            self._encoder_left.deinit()
        
        if self._encoder_right is not None:
            self._encoder_right.deinit()


'''def yoto_init(**kwargs):
    """
    Initialize a YotoMini
    
    :return: Initialized YotoMini instance
    """
    return YotoMini(**kwargs)'''
