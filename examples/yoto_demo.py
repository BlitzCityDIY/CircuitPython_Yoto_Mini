# SPDX-FileCopyrightText: 2026 Liz Clark for Adafruit Industries
# SPDX-License-Identifier: MIT

"""
Complete example demonstrating all Yoto Mini features
"""

import time
import array
import math
import audiocore
from circuitpython_yoto import YotoMini

# Initialize Yoto Mini with all peripherals
yoto = YotoMini()

print("Yoto Mini Demo")

# Display RTC time if available
if yoto.rtc_valid:
    dt = yoto.datetime
    print(f"\nCurrent Time: {dt.tm_year}-{dt.tm_mon:02d}-{dt.tm_mday:02d} "
          f"{dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}")
else:
    print("RTC needs to be set")
# Example of setting time:
# t = time.struct_time((2026, 1, 17, 15, 28, 0, 5, -1, -1))
# yoto.datetime = t

# Display battery status
if yoto.battery is not None:
    status = yoto.charge_status
    print(f"\nBattery Status:")
    print(f"  Charge State: {status['charge_status']}")
    print(f"  VBUS: {status['vbus_status']}")
    print(f"  Power Good: {status['power_good']}")
    print(f"  Voltage: {yoto.charge_voltage}mV")
    print(f"  Current: {yoto.charge_current}mA")

# Generate a simple tone for testing
print("\nGenerating 440Hz test tone...")
tone_volume = 0.3
frequency = 440
sample_rate = 44100
length = sample_rate // frequency

sine_wave = array.array("h", [0] * length)
for i in range(length):
    sine_wave[i] = int((math.sin(math.pi * 2 * i / length)) * tone_volume * (2**15 - 1))

sine_wave_sample = audiocore.RawSample(sine_wave, sample_rate=sample_rate)

# Set initial volume
yoto.volume = 150
print(f"Volume set to: {yoto.volume}")

print("-" * 60)
print("  - Scan NFC tags")
print("  - Turn left encoder to adjust volume")
print("  - Press left encoder button to toggle audio")
print("  - Press right encoder button to check battery")
print("-" * 60)

# Start playing tone
yoto.play(sine_wave_sample, loop=True)

last_encoder_left = yoto.encoder_left_position
last_encoder_right = yoto.encoder_right_position
last_button1 = False
last_button2 = False
last_tag_uid = None
audio_playing = True

while True:
    # Check for NFC tags
    uid, sak = yoto.read_nfc_tag()
    if uid and uid != last_tag_uid:
        last_tag_uid = uid
        print(f"\nNFC Tag Detected!")
        print(f"   UID: {uid.hex().upper()}")
        print(f"   Type: {yoto.get_card_type(sak)}\n")
    elif uid is None:
        last_tag_uid = None
    
    # Check encoder 1 (volume control)
    if yoto.encoder_left_position != last_encoder_left:
        current_left = yoto.encoder_left_position
        diff = current_left - last_encoder_left
        new_volume = max(0, min(255, yoto.volume + (diff * 5)))
        yoto.volume = new_volume
        print(f"Volume: {yoto.volume}")
        last_encoder_left = yoto.encoder_left_position
    
    # Check encoder 1 button (toggle audio)
    button1 = yoto.encoder_left_button
    if button1 and not last_button1:  # Button pressed
        audio_playing = not audio_playing
        if audio_playing:
            yoto.mute = False
            print("Audio playing")
        else:
            yoto.mute = True
            print("Audio muted")
    last_button1 = button1
    
    # Check encoder 2
    if yoto.encoder_right_position != last_encoder_right:
        print(f"Right encoder: {yoto.encoder_right_position}")
        last_encoder_right = yoto.encoder_right_position
    
    # Check encoder 2 button (battery status)
    button2 = yoto.encoder_right_button
    if button2 and not last_button2:  # Button pressed
        if yoto.battery is not None:
            status = yoto.charge_status
            print(f"\nBattery: {status['charge_status']} | {status['vbus_status']}")
            if yoto.charging:
                print("   Charging...")
            elif yoto.charge_complete:
                print("   Fully charged")
            print()
    last_button2 = button2
    
    time.sleep(0.05)