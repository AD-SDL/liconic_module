"""
Example file to demonstrate usage of the LiCONiC incubator interface through python

This example assumes a device configuration of micrplate stacks in stacks 1 and 2,
 and deepwell stacks in stacks 3 and 4. Please edit to suit your needs.


 TODOs:
- TEST!
"""

# make sure you're running this example from a directory that allows importing this interface
from liconic_interface.liconic_interface import LICONIC

device = LICONIC(host="localhost", port=3333)

# CLIMATE CONTROLS
print("\nReading actual climate")
climate = device.read_actual_climate()
temp, humidity, co2, n2 = climate
print(f"Actual climate: {temp=}, {humidity=}, {co2=}, {n2=}")

print("\nSetting climate to 37 deg C and 95 percent humidity")
print("Note: our device doesn't allow for CO2 or N2 control")
device.write_set_climate(temperature=37.0, humidity=95.0)

print("\nReading set climate")
climate = device.read_set_climate()
temp, humidity, co2, n2 = climate
print(f"Set climate: {temp=}, {humidity=}, {co2=}, {n2=}")

# SHAKER CONTROLS
print("\nActivate shaker 1 (stacks 1 and 2) at speed 20 (200 rpm)")
device.activate_shaker(shaker_id=1, speed=20)
print("\nReading set shaker speed of shaker 1")
print(f"Shaker 1 set speed: {device.read_set_shaker_speed(shaker_id=1)}")
print("\nDeactivate shaker 1")
device.deactivate_shaker(shaker_id=1)

print("\nActivate shaker 2 (stacks 3 and 4) at speed 40 (400 rpm)")
device.activate_shaker(shaker_id=2, speed=40)
print("\nReading set shaker speed of shaker 2")
print(f"Shaker 2 set speed: {device.read_set_shaker_speed(shaker_id=2)}")
print("\nDeactivate shaker 2")
device.deactivate_shaker(shaker_id=2)

# PLATE HANDLING METHOD
"""
NOTE: You need to ensure that your plate type is compatible with the specified stack/slot!
This interface will NOT check for you.
"""
print("Loading microplate into stack 1 slot 1")
device.load_plate(stack=1, slot=1)

print("Unloading plate from stack 1, slot 1")
device.unload_plate(stack=1, slot=1)
