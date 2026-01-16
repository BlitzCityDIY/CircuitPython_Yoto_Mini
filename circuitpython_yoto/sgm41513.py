# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
CircuitPython driver for SGM41513 Battery Charger IC
"""

from adafruit_bus_device.i2c_device import I2CDevice
from adafruit_register.i2c_bit import RWBit
from adafruit_register.i2c_bits import RWBits, ROBits
from micropython import const

# I2C Address
_DEFAULT_ADDRESS = const(0x1A)

# Register addresses
_INPUT_SOURCE = const(0x00)
_POWER_ON_CONFIG = const(0x01)
_CHARGE_CURRENT = const(0x02)
_PRECHARGE_TERM = const(0x03)
_CHARGE_VOLTAGE = const(0x04)
_CHARGE_TERM_TIMER = const(0x05)
_BOOST_THERMAL = const(0x06)
_MISC_OPERATION = const(0x07)
_SYSTEM_STATUS = const(0x08)
_FAULT = const(0x09)
_VINDPM_STATUS = const(0x0A)
_PART_INFO = const(0x0B)


class SGM41513:
    """Driver for SGM41513 Battery Charger IC"""
    
    # REG00 - Input Source Control
    hiz_mode = RWBit(_INPUT_SOURCE, 7)
    """Enable HIZ mode (disconnect VBUS from internal circuit)"""
    
    _iindpm_raw = RWBits(5, _INPUT_SOURCE, 0)
    
    # REG01 - Power-On Configuration
    charge_enabled = RWBit(_POWER_ON_CONFIG, 4)
    """Enable or disable battery charging"""
    
    otg_enabled = RWBit(_POWER_ON_CONFIG, 5)
    """Enable or disable OTG (boost) mode"""
    
    _watchdog_reset = RWBit(_POWER_ON_CONFIG, 6)
    
    # REG02 - Charge Current Control
    _ichg_raw = RWBits(6, _CHARGE_CURRENT, 0)
    
    # REG03 - Pre-Charge/Termination Current Control
    _iprechg_raw = RWBits(4, _PRECHARGE_TERM, 4)
    _iterm_raw = RWBits(4, _PRECHARGE_TERM, 0)
    
    # REG04 - Charge Voltage Control
    _vreg_raw = RWBits(5, _CHARGE_VOLTAGE, 3)
    
    # REG05 - Charge Termination/Timer Control
    termination_enabled = RWBit(_CHARGE_TERM_TIMER, 7)
    """Enable or disable charge termination"""
    
    safety_timer_enabled = RWBit(_CHARGE_TERM_TIMER, 3)
    """Enable or disable charging safety timer"""
    
    _watchdog_timer = RWBits(2, _CHARGE_TERM_TIMER, 4)
    
    # REG06 - Boost Voltage/Thermal Regulation Control
    _boostv_raw = RWBits(2, _BOOST_THERMAL, 4)
    
    # REG07 - Misc Operation Control
    batfet_disable = RWBit(_MISC_OPERATION, 5)
    """Disable BATFET (disconnect battery from system)"""
    
    # REG08 - System Status (Read-Only)
    _vbus_stat = ROBits(3, _SYSTEM_STATUS, 5)
    _chrg_stat = ROBits(2, _SYSTEM_STATUS, 3)
    _pg_stat = ROBits(1, _SYSTEM_STATUS, 2)
    _therm_stat = ROBits(1, _SYSTEM_STATUS, 1)
    _vsys_stat = ROBits(1, _SYSTEM_STATUS, 0)
    
    # REG09 - Fault Status (Read-Only)
    _watchdog_fault = ROBits(1, _FAULT, 7)
    _boost_fault = ROBits(1, _FAULT, 6)
    _chrg_fault = ROBits(2, _FAULT, 4)
    _bat_fault = ROBits(1, _FAULT, 3)
    _ntc_fault = ROBits(3, _FAULT, 0)
    
    # REG0A - VINDPM Status (Read-Only)
    _vbus_gd = ROBits(1, _VINDPM_STATUS, 7)
    _vindpm_stat = ROBits(1, _VINDPM_STATUS, 6)
    _iindpm_stat = ROBits(1, _VINDPM_STATUS, 5)
    _topoff_active = ROBits(1, _VINDPM_STATUS, 3)
    _acov_stat = ROBits(1, _VINDPM_STATUS, 2)
    
    # REG0B - Part Information (Read-Only)
    _pn = ROBits(4, _PART_INFO, 3)
    _dev_rev = ROBits(2, _PART_INFO, 0)
    
    def __init__(self, i2c, address=_DEFAULT_ADDRESS):
        """Initialize the SGM41513
        
        :param ~busio.I2C i2c: The I2C bus the device is connected to
        :param int address: The I2C device address. Defaults to :const:`0x1A`
        """
        self.i2c_device = I2CDevice(i2c, address)
    
    @property
    def part_info(self):
        """Part number and revision information
        
        :return: Dictionary with part_number and revision
        :rtype: dict
        """
        pn = self._pn
        rev = self._dev_rev
        
        part_names = {
            0b0000: "SGM41513",
            0b0001: "SGM41513A/SGM41513D"
        }
        
        return {
            "part_number": part_names.get(pn, f"Unknown (0x{pn:X})"),
            "revision": rev
        }
    
    @property
    def system_status(self):
        """Current system status
        
        :return: Dictionary with VBUS status, charge status, power good, thermal regulation, and VSYS regulation
        :rtype: dict
        """
        vbus_stat = self._vbus_stat
        chrg_stat = self._chrg_stat
        
        vbus_names = {
            0b000: "No Input",
            0b001: "USB SDP",
            0b010: "Adapter",
            0b011: "USB CDP",
            0b101: "Unknown Adapter",
            0b110: "Non-standard Adapter",
            0b111: "OTG"
        }
        
        chrg_names = {
            0b00: "Disabled",
            0b01: "Pre-charge",
            0b10: "Fast Charge",
            0b11: "Complete"
        }
        
        return {
            "vbus_status": vbus_names.get(vbus_stat, f"Unknown (0b{vbus_stat:03b})"),
            "vbus_stat_code": vbus_stat,
            "charge_status": chrg_names.get(chrg_stat, f"Unknown (0b{chrg_stat:02b})"),
            "charge_stat_code": chrg_stat,
            "power_good": bool(self._pg_stat),
            "thermal_regulation": bool(self._therm_stat),
            "vsys_regulation": bool(self._vsys_stat)
        }
    
    @property
    def fault_status(self):
        """Current fault status
        
        :return: Dictionary with watchdog, boost, charge, battery, and NTC fault status
        :rtype: dict
        """
        chrg_fault = self._chrg_fault
        
        chrg_fault_names = {
            0b00: "Normal",
            0b01: "Input fault",
            0b10: "Thermal shutdown",
            0b11: "Safety timer expired"
        }
        
        return {
            "watchdog_fault": bool(self._watchdog_fault),
            "boost_fault": bool(self._boost_fault),
            "charge_fault": chrg_fault_names.get(chrg_fault, "Unknown"),
            "charge_fault_code": chrg_fault,
            "battery_fault": bool(self._bat_fault),
            "ntc_fault": self._ntc_fault
        }
    
    @property
    def vindpm_status(self):
        """Input voltage/current DPM status
        
        :return: Dictionary with VBUS good, VINDPM, IINDPM, top-off, and ACOV status
        :rtype: dict
        """
        return {
            "vbus_good": bool(self._vbus_gd),
            "vindpm_active": bool(self._vindpm_stat),
            "iindpm_active": bool(self._iindpm_stat),
            "topoff_active": bool(self._topoff_active),
            "acov_active": bool(self._acov_stat)
        }
    
    @property
    def charge_current(self):
        """Charge current setting in mA
        
        :return: Charge current in milliamps
        :rtype: int
        """
        code = self._ichg_raw
        
        # Decode based on datasheet Table 10
        if code <= 0x0F:
            currents = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 110]
            return currents[code] if code < len(currents) else 110
        elif code <= 0x1F:
            return 130 + (code - 0x10) * 20
        elif code <= 0x2F:
            return 540 + (code - 0x20) * 60
        else:
            return min(1500 + (code - 0x30) * 120, 3000)
    
    @charge_current.setter
    def charge_current(self, current_ma):
        """Set charge current in mA (0-3000mA)
        
        :param int current_ma: Desired charge current in milliamps
        """
        current_ma = max(0, min(3000, current_ma))
        
        if current_ma <= 110:
            values = [0, 5, 10, 15, 20, 25, 30, 35, 40, 50, 60, 70, 80, 90, 100, 110]
            code = min(range(len(values)), key=lambda i: abs(values[i] - current_ma))
        elif current_ma <= 510:
            code = 0x10 + (current_ma - 130) // 20
        elif current_ma <= 1440:
            code = 0x20 + (current_ma - 540) // 60
        else:
            code = 0x30 + (current_ma - 1500) // 120
        
        self._ichg_raw = code
    
    @property
    def charge_voltage(self):
        """Charge voltage setting in mV
        
        :return: Charge voltage in millivolts
        :rtype: int
        """
        code = self._vreg_raw
        
        if code == 0x0F:
            return 4350
        elif code <= 24:
            return 3856 + (code * 32)
        else:
            return 4624
    
    @charge_voltage.setter
    def charge_voltage(self, voltage_mv):
        """Set charge voltage in mV (3856-4624mV)
        
        :param int voltage_mv: Desired charge voltage in millivolts
        """
        voltage_mv = max(3856, min(4624, voltage_mv))
        
        if voltage_mv == 4350:
            code = 0x0F
        else:
            code = min(24, (voltage_mv - 3856) // 32)
        
        self._vreg_raw = code
    
    @property
    def input_current_limit(self):
        """Input current limit in mA
        
        :return: Input current limit in milliamps
        :rtype: int
        """
        return 100 + (self._iindpm_raw * 100)
    
    @input_current_limit.setter
    def input_current_limit(self, current_ma):
        """Set input current limit in mA (100-3200mA)
        
        :param int current_ma: Desired input current limit in milliamps
        """
        current_ma = max(100, min(3200, current_ma))
        self._iindpm_raw = (current_ma - 100) // 100
    
    @property
    def precharge_current(self):
        """Precharge current limit in mA
        
        :return: Precharge current in milliamps
        :rtype: int
        """
        return 60 + (self._iprechg_raw * 60)
    
    @precharge_current.setter
    def precharge_current(self, current_ma):
        """Set precharge current limit in mA (60-960mA)
        
        :param int current_ma: Desired precharge current in milliamps
        """
        current_ma = max(60, min(960, current_ma))
        self._iprechg_raw = (current_ma - 60) // 60
    
    @property
    def termination_current(self):
        """Termination current limit in mA
        
        :return: Termination current in milliamps
        :rtype: int
        """
        return 60 + (self._iterm_raw * 60)
    
    @termination_current.setter
    def termination_current(self, current_ma):
        """Set termination current limit in mA (60-960mA)
        
        :param int current_ma: Desired termination current in milliamps
        """
        current_ma = max(60, min(960, current_ma))
        self._iterm_raw = (current_ma - 60) // 60
    
    @property
    def watchdog_timer(self):
        """Watchdog timer setting
        
        :return: Timer setting ('Disabled', '40s', '80s', or '160s')
        :rtype: str
        """
        timers = {0: "Disabled", 1: "40s", 2: "80s", 3: "160s"}
        return timers.get(self._watchdog_timer, "Unknown")
    
    @watchdog_timer.setter
    def watchdog_timer(self, setting):
        """Set watchdog timer
        
        :param str setting: Timer setting ('Disabled', '40s', '80s', or '160s')
        """
        timers = {"Disabled": 0, "40s": 1, "80s": 2, "160s": 3}
        self._watchdog_timer = timers.get(setting, 3)
    
    @property
    def boost_voltage(self):
        """Boost mode (OTG) output voltage in mV
        
        :return: Boost voltage in millivolts
        :rtype: int
        """
        voltages = {0: 4850, 1: 5000, 2: 5150, 3: 5300}
        return voltages.get(self._boostv_raw, 5150)
    
    @boost_voltage.setter
    def boost_voltage(self, voltage_mv):
        """Set boost mode output voltage
        
        :param int voltage_mv: Desired voltage (4850, 5000, 5150, or 5300 mV)
        """
        voltage_map = {4850: 0, 5000: 1, 5150: 2, 5300: 3}
        # Find closest match
        closest = min(voltage_map.keys(), key=lambda x: abs(x - voltage_mv))
        self._boostv_raw = voltage_map[closest]
    
    def reset_watchdog(self):
        """Reset the watchdog timer"""
        self._watchdog_reset = True
    
    def reset_registers(self):
        """Reset all registers to default values"""
        # Write to REG0B bit 7 to reset
        with self.i2c_device as i2c:
            i2c.write(bytes([_PART_INFO, 0x80]))
