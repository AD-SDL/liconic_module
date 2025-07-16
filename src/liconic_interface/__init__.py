"""Liconic Interface for interacting with the STX library"""

import threading
from ctypes import CDLL, c_bool, c_char_p, c_float, c_int, pointer
from pathlib import Path


class Stx:
    """A class for interacting with a Liconic incubator device via the Liconic STX library."""

    try:
        lib = CDLL(Path(__file__).parent / "libstxlib.so")
    except Exception as e:
        print(f"Failed to load the STX library: {e}")

    def __init__(self, device="/dev/ttyUSB0"):
        """Initializes an STX object for interacting with a Liconic incubator
        device via the Liconic STX library."""
        self.lock = threading.Lock()
        self.device = device
        self.connect_and_initialize(self.device)

    def __del__(self):
        """Closes the serial connection on cleanup"""
        self.lib.Disconnect(self.id)
        print("Disconnected from Liconic")

    def connect_and_initialize(self, device="/dev/ttyUSB0"):
        """Connects to the Liconic device and initializes it if necessary."""
        with self.lock:
            self.id = self.lib.Connect(c_char_p(bytes(device, encoding="utf-8")))
            if self.id < 0:
                raise Exception(
                    f"Failed to connect to Liconic with error code: {self.id}"
                )
            print("Connected to Liconic")
            is_initialized = c_bool()
            self.lib.ReadIsInitialized(self.id, pointer(is_initialized))
            if not is_initialized:
                print("Liconic not initialized, initializing...")
                self.lib.Initialize(self.id)
                print("Liconic initialized.")

    @property
    def current_temperature(self):
        """Gets the current temperature of the incubator."""
        with self.lock:
            temp = c_float()
            result = self.lib.ReadTemperature(self.id, pointer(temp))
            if result < 0:
                raise Exception(f"Error reading temperature: {result}")
            return temp.value

    @property
    def target_temperature(self):
        """Gets the target temperature of the incubator."""
        with self.lock:
            temp = c_float()
            result = self.lib.ReadSetTemperature(self.id, pointer(temp))
            if result < 0:
                raise Exception(f"Error reading target temperature: {result}")
            return temp.value

    @target_temperature.setter
    def target_temperature(self, temperature: float) -> bool:
        """Sets the target temperature of the incubator."""
        with self.lock:
            result = self.lib.SetTemperature(self.id, c_float(temperature))
            if result < 0:
                raise Exception(f"Error setting temperature: {result}")

    @property
    def current_humidity(self):
        """Gets the current humidity of the incubator."""
        with self.lock:
            humidity = c_float()
            result = self.lib.ReadHumidity(self.id, pointer(humidity))
            if result < 0:
                raise Exception(f"Error reading humidity: {result}")
            return humidity.value

    @property
    def target_humidity(self):
        """Gets the target humidity of the incubator"""
        with self.lock:
            humidity = c_float()
            result = self.lib.ReadSetHumidity(self.id, pointer(humidity))
            if result < 0:
                raise Exception(f"Error reading target humidity: {result}")
            return humidity.value

    @target_humidity.setter
    def target_humidity(self, humidity: float):
        """Sets the target humidity of the incubator."""
        with self.lock:
            result = self.lib.SetHumidity(self.id, c_float(humidity))
            if result < 0:
                raise Exception(f"Error setting humidity: {result}")

    @property
    def shaker_speed(self):
        """Gets the speed of the shaker."""
        with self.lock:
            speed = c_int()
            result = self.lib.ReadShakerSpeed(self.id, pointer(speed))
            if result < 0:
                raise Exception(f"Error reading shaker speed: {result}")
            return speed.value

    @shaker_speed.setter
    def shaker_speed(self, speed: int) -> bool:
        """Sets the speed of the shaker."""
        with self.lock:
            result = self.lib.SetShakerSpeed(self.id, c_int(speed))
            if result < 0:
                raise Exception(f"Error setting shaker speed: {result}")

    def activate_shaker(self):
        """Activates the shaker."""

    @property
    def shaker_active(self):
        """Returns whether the shaker is active."""
        if not hasattr(self, "_shaker_is_active"):
            self._shaker_is_active = False
        return self._shaker_is_active

    @shaker_active.setter
    def shaker_active(self, is_active: bool):
        """Sets whether the shaker is active."""
        with self.lock:
            result = self.lib.RunShaker(self.id, c_bool(is_active))
            if result < 0:
                raise Exception(f"Error activating shaker: {result}")
        self._shaker_is_active = is_active

    @property
    def shovel_occupied(self) -> bool:
        """Returns whether a plate is in the shovel."""
        with self.lock:
            plate_in_shovel = c_bool()
            result = self.lib.ReadShovelDetector(self.id, pointer(plate_in_shovel))
            if result < 0:
                raise Exception(f"Error reading plate in shovel: {result}")
            return plate_in_shovel.value

    @property
    def transfer_station_occupied(self) -> bool:
        """Returns whether a plate is in the transfer station."""
        with self.lock:
            plate_in_transfer_station = c_bool()
            result = self.lib.ReadXferDetector(
                self.id, pointer(plate_in_transfer_station)
            )
            if result < 0:
                raise Exception(f"Error reading plate in transfer station: {result}")
            return plate_in_transfer_station.value

    @property
    def transfer_station_2_occupied(self) -> bool:
        """Returns whether a plate is in transfer station 2."""
        with self.lock:
            plate_in_transfer_station = c_bool()
            result = self.lib.ReadXferDetector2(
                self.id, pointer(plate_in_transfer_station)
            )
            if result < 0:
                raise Exception(f"Error reading plate in transfer station2: {result}")
            return plate_in_transfer_station.value

    def slot_occupied(self, stacker: int, slot: int) -> bool:
        """Returns whether a plate is in the specified slot."""
        with self.lock:
            plate_in_slot = c_bool()
            result = self.lib.ReadPlatePresence(
                self.id, c_int(stacker), c_int(slot), pointer(plate_in_slot)
            )
            if result < 0:
                raise Exception(f"Error reading plate in slot: {result}")
            return plate_in_slot.value

    def load_plate(self, stacker: int, slot: int) -> bool:
        """Loads a plate into the specified slot."""
        with self.lock:
            result = self.lib.LoadPlate(self.id, c_int(stacker), c_int(slot))
            if result < 0:
                raise Exception(f"Error loading plate: {result}")
            return result

    def unload_plate(self, stacker: int, slot: int) -> bool:
        """Unloads a plate from the specified slot."""
        with self.lock:
            result = self.lib.UnloadPlate(self.id, c_int(stacker), c_int(slot))
            if result < 0:
                raise Exception(f"Error unloading plate: {result}")
            return result

    def pick_plate(self, stacker: int, slot: int) -> bool:
        """Picks up a plate from the specified slot, holding it in the shovel."""
        with self.lock:
            result = self.lib.PickPlate(self.id, c_int(stacker), c_int(slot))
            if result < 0:
                raise Exception(f"Error picking plate: {result}")
            return result

    def place_plate(self, stacker: int, slot: int) -> bool:
        """Places a plate in the specified slot."""
        with self.lock:
            result = self.lib.PlacePlate(self.id, c_int(stacker), c_int(slot))
            if result < 0:
                raise Exception(f"Error placing plate: {result}")
            return result

    def get_plate(self) -> bool:
        """Picks up a plate from the transfer station, holding it in the shovel."""
        with self.lock:
            result = self.lib.GetPlate(self.id)
            if result < 0:
                raise Exception(f"Error getting plate: {result}")
            return result

    def set_plate(self) -> bool:
        """Places a plate in the transfer station."""
        with self.lock:
            result = self.lib.SetPlate(self.id)
            if result < 0:
                raise Exception(f"Error setting plate: {result}")
            return result

    @property
    def is_busy(self) -> bool:
        """Returns whether the incubator is busy."""
        if self.lock.locked():
            return True
        with self.lock:
            busy = c_bool()
            result = self.lib.ReadIsBusy(self.id, pointer(busy))
            if result < 0:
                raise Exception(f"Error reading busy status: {result}")
            return busy.value


if __name__ == "__main__":
    stx = Stx()
    print(stx.read_temperature())
