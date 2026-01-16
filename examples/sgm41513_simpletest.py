# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Simple demo for SGM41513 Battery Charger
Reads and displays current charger status
"""
import board
import busio
import time
from sgm41513 import SGM41513

i2c = board.I2C()

charger = SGM41513(i2c)

print("="*60)
print("SGM41513 Battery Charger - Status Reader")
print("="*60)

# Read part information
part = charger.part_info
print(f"\nPart: {part['part_number']}")
print(f"Revision: {part['revision']}")

# Read system status
print("\n" + "-"*60)
print("System Status")
print("-"*60)
status = charger.system_status
print(f"VBUS: {status['vbus_status']}")
print(f"Charge State: {status['charge_status']}")
print(f"Power Good: {status['power_good']}")
print(f"Thermal Regulation: {status['thermal_regulation']}")
print(f"VSYS Regulation: {status['vsys_regulation']}")

# Read fault status
print("\n" + "-"*60)
print("Fault Status")
print("-"*60)
fault = charger.fault_status
print(f"Watchdog Fault: {fault['watchdog_fault']}")
print(f"Boost Fault: {fault['boost_fault']}")
print(f"Charge Fault: {fault['charge_fault']}")
print(f"Battery Fault: {fault['battery_fault']}")

# Read DPM status
print("\n" + "-"*60)
print("DPM Status")
print("-"*60)
dpm = charger.vindpm_status
print(f"VBUS Good: {dpm['vbus_good']}")
print(f"VINDPM Active: {dpm['vindpm_active']}")
print(f"IINDPM Active: {dpm['iindpm_active']}")
print(f"Top-off Active: {dpm['topoff_active']}")

# Read charger settings
print("\n" + "-"*60)
print("Charger Settings")
print("-"*60)
print(f"Charge Current: {charger.charge_current}mA")
print(f"Charge Voltage: {charger.charge_voltage}mV")
print(f"Input Current Limit: {charger.input_current_limit}mA")
print(f"Precharge Current: {charger.precharge_current}mA")
print(f"Termination Current: {charger.termination_current}mA")
print(f"Charge Enabled: {charger.charge_enabled}")
print(f"OTG Enabled: {charger.otg_enabled}")
print(f"HIZ Mode: {charger.hiz_mode}")
print(f"Watchdog Timer: {charger.watchdog_timer}")
print(f"Boost Voltage: {charger.boost_voltage}mV")

while True:
	status = charger.system_status
	
	print(f"Status: {status['charge_status']:12s} | "
		  f"VBUS: {status['vbus_status']:12s} | "
		  f"Power: {'Good' if status['power_good'] else 'No':4s} | "
		  f"{charger.charge_current:4d}mA @ {charger.charge_voltage:4d}mV")
	
	time.sleep(2)
