# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython driver for the TCAL6416 (TCA6416A) 16-bit I/O Expander
"""

from adafruit_bus_device.i2c_device import I2CDevice
from micropython import const

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/yourrepo/CircuitPython_TCAL6416.git"

# Register addresses
_INPUT_PORT_0 = const(0x00)
_INPUT_PORT_1 = const(0x01)
_OUTPUT_PORT_0 = const(0x02)
_OUTPUT_PORT_1 = const(0x03)
_POLARITY_INV_PORT_0 = const(0x04)
_POLARITY_INV_PORT_1 = const(0x05)
_CONFIG_PORT_0 = const(0x06)  # Direction register for Port 0
_CONFIG_PORT_1 = const(0x07)  # Direction register for Port 1


class TCAL6416:
    """
    Driver for the TCAL6416/TCA6416A 16-bit I/O Expander.
    
    :param ~busio.I2C i2c_bus: The I2C bus the device is connected to
    :param int address: The I2C device address (default: 0x20)
    """
    
    def __init__(self, i2c_bus, address=0x20):
        self.i2c_device = I2CDevice(i2c_bus, address)
        self._port0_output = 0x00
        self._port1_output = 0x00
        
    def _write_register(self, reg, value):
        """Write a single byte to a register."""
        with self.i2c_device as i2c:
            i2c.write(bytes([reg, value]))
    
    def _read_register(self, reg):
        """Read a single byte from a register."""
        buf = bytearray(1)
        with self.i2c_device as i2c:
            i2c.write_then_readinto(bytes([reg]), buf)
        return buf[0]
    
    def configure_port0_direction(self, direction):
        """
        Configure Port 0 pin directions.
        
        :param int direction: 8-bit value where 1=input, 0=output
        """
        self._write_register(_CONFIG_PORT_0, direction)
    
    def configure_port1_direction(self, direction):
        """
        Configure Port 1 pin directions.
        
        :param int direction: 8-bit value where 1=input, 0=output
        """
        self._write_register(_CONFIG_PORT_1, direction)
    
    def set_port0_output(self, value):
        """
        Set Port 0 output values.
        
        :param int value: 8-bit value for output pins
        """
        self._port0_output = value
        self._write_register(_OUTPUT_PORT_0, value)
    
    def set_port1_output(self, value):
        """
        Set Port 1 output values.
        
        :param int value: 8-bit value for output pins
        """
        self._port1_output = value
        self._write_register(_OUTPUT_PORT_1, value)
    
    def set_pin(self, pin, value):
        """
        Set a single pin HIGH or LOW.
        
        :param int pin: Pin number (0-15, where 0-7 is Port0, 8-15 is Port1)
        :param bool value: True for HIGH, False for LOW
        """
        if pin < 8:
            # Port 0
            if value:
                self._port0_output |= (1 << pin)
            else:
                self._port0_output &= ~(1 << pin)
            self.set_port0_output(self._port0_output)
        else:
            # Port 1
            pin = pin - 8
            if value:
                self._port1_output |= (1 << pin)
            else:
                self._port1_output &= ~(1 << pin)
            self.set_port1_output(self._port1_output)
    
    def get_pin(self, pin):
        """
        Read a single pin state.
        
        :param int pin: Pin number (0-15)
        :return: True if HIGH, False if LOW
        """
        if pin < 8:
            # Port 0
            value = self._read_register(_INPUT_PORT_0)
            return bool(value & (1 << pin))
        else:
            # Port 1
            pin = pin - 8
            value = self._read_register(_INPUT_PORT_1)
            return bool(value & (1 << pin))
    
    def configure_yoto_mini_defaults(self):
        """
        Configure the IO expander with Yoto Mini defaults.
        
        Based on firmware values:
        - Port 0 direction: 0xB0 (binary: 10110000)
          Pins 7,5,4 = input (1), pins 6,3,2,1,0 = output (0)
          P0_2 is OUTPUT for amplifier reset
        - Port 1 direction: 0xAF (binary: 10101111)
          Pins 7,5,3,2,1,0 = input (1), pins 6,4 = output (0)
        
        Where 1 = input, 0 = output in configuration register
        """
        
        # Read current configuration to show before/after
        current_config0 = self._read_register(_CONFIG_PORT_0)
        current_config1 = self._read_register(_CONFIG_PORT_1)
        
        # Port 0: 0xB0 = 10110000 (P0_2 = OUTPUT bit 2 = 0)
        self.configure_port0_direction(0xB0)
        
        # Port 1: 0xAF = 10101111
        self.configure_port1_direction(0xAF)
        
        # Verify
        new_config0 = self._read_register(_CONFIG_PORT_0)
        new_config1 = self._read_register(_CONFIG_PORT_1)
        
        # Read current output state
        current_out0 = self._read_register(_OUTPUT_PORT_0)
        current_out1 = self._read_register(_OUTPUT_PORT_1)
        
        # Initialize outputs: Start with all outputs LOW (0x00)
        # This ensures amplifier starts in reset
        self._port0_output = 0x00
        self._port1_output = 0x00
        self.set_port0_output(0x00)
        self.set_port1_output(0x00)
        
        # Verify
        new_out0 = self._read_register(_OUTPUT_PORT_0)
        new_out1 = self._read_register(_OUTPUT_PORT_1)