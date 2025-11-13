"""Python interface for connecting to and utilizing the LiCONiC StoreX TCP/IP Windows driver."""

import argparse
import datetime
import logging
import socket
import threading


class LICONIC:
    """Python interface for control of the LiCONiC STX88 incubator"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3333,
    ) -> socket.socket:
        """Creates LiCONiC interface and connects to the device."""

        # set up logging
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            filename="liconic_interface.log",
            level=logging.DEBUG,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
        self.lock = threading.Lock()

        # connection parameters
        self.port = port
        self.host = host
        self.device_ID = "STX"
        self.c_socket = None

        # connect and activate
        self.connect()
        self.activate()

    def __del__(self) -> None:
        """Cleans up the LiCONiC interface."""
        self.deactivate()
        self.disconnect()

    def connect(self) -> None:
        """Connects to the LiCONiC device and initializes it if necessary."""
        with self.lock:
            server_address = (self.host, self.port)
            c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            c_socket.connect(server_address)
            self.c_socket = c_socket

    def disconnect(self) -> None:
        """Disconnects from the LiCONiC device."""
        if self.c_socket:
            with self.lock:
                self.c_socket.close()
                self.c_socket = None

    def activate(self) -> None:
        """Opens serial communication and initializes the StoreX incubator."""
        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Activating LiCONiC")
            self.c_socket.send(f"STX2Activate({self.device_ID})\r".encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    def deactivate(self) -> None:
        """
        Closes serial communication with the StoreX incubator.
        Empty feedback response expected.
        """
        if self.c_socket:
            with self.lock:
                self.logger.debug(f"{datetime.datetime.now()} - Deactivating LiCONiC")
                self.c_socket.send(f"STX2Deactivate({self.device_ID})\r".encode())
                feedback = self.c_socket.recv(1024).decode().strip()
                self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    def reset(self) -> None:
        """Resets the StoreX incubator. Empty feedback response expected."""
        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Resetting LiCONiC")
            self.c_socket.send(f"STX2Reset({self.device_ID})\r".encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    def soft_reset(self) -> None:
        # WHAT IS A SOFT RESET???
        """Performs a soft reset of the StoreX incubator. Empty feedback response expected."""
        with self.lock:
            self.logger.debug(
                f"{datetime.datetime.now()} - Performing soft reset of LiCONiC"
            )
            self.c_socket.send(f"STX2SoftReset({self.device_ID})\r".encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    # CLIMATE CONTROL METHODS
    def read_actual_climate(self) -> list[float]:
        """
        Reads the actual climate data from the StoreX incubator.

        Returns:
            list: A list of floats containing the actual climate data.
            [0]= temperature (°C)
            [1]= relative humidity (%)
            [2]= CO2 concentration (ppm)
            [3]= N2 concentration (%)
        """
        with self.lock:
            actual_climate = []
            self.logger.debug(f"{datetime.datetime.now()} - Reading actual climate")
            self.c_socket.send(f"STX2ReadActualClimate({self.device_ID})\r".encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            actual_climate = feedback.split(";")
            actual_climate = [
                float(value) for value in actual_climate
            ]  # convert strings to floats
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")
            self.logger.debug(
                f"{datetime.datetime.now()} - Actual Climate Data: {actual_climate}"
            )
            return actual_climate

    def write_set_climate(
        self,
        temperature: float = 37.0,
        humidity: float = 95.0,
        co2: float = 10.0,
        n2: float = 0.0,
    ) -> None:
        """
        Writes the desired climate settings to the StoreX incubator.
        Blank feedback response expected.

        Args:
            temperature (float): Desired temperature in °C.
            humidity (float): Desired relative humidity in %.
            co2 (float): Desired CO2 concentration in ppm.
            n2 (float): Desired N2 concentration in %.
        """
        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Writing set climate")
            command = f"STX2WriteSetClimate({self.device_ID},{temperature},{humidity},{co2},{n2})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    def read_set_climate(self) -> list[float]:
        """
        Reads the desired climate settings from the StoreX incubator.

        Returns:
            list: A list of floats containing the set climate data.
            [0]= temperature (°C)
            [1]= relative humidity (%)
            [2]= CO2 concentration (ppm)
            [3]= N2 concentration (%)
        """
        with self.lock:
            set_climate = []
            self.logger.debug(f"{datetime.datetime.now()} - Reading set climate")
            self.c_socket.send(f"STX2ReadSetClimate({self.device_ID})\r".encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            set_climate = feedback.split(";")
            set_climate = [
                float(value) for value in set_climate
            ]  # convert strings to floats
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")
            self.logger.debug(
                f"{datetime.datetime.now()} - Set Climate Data: {set_climate}"
            )
            return set_climate

    # SHAKER CONTROL METHODS
    def activate_shaker(self, shaker_id: int = None, speed: int = 20) -> None:
        """
        Activates the specified shaker at the specified speed.
        Blank feedback response expected.

        Args:
            shaker_id (int): shaker iD (1 or 2).
            speed (int): Shaker speed in rpm (1-50).

        """
        if shaker_id not in [1, 2]:
            raise ValueError("shaker_id must be 1 or 2.")
        if speed < 1 or speed > 50:
            raise ValueError("speed must be between 1 and 50 rpm.")

        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Activating shaker")
            command = f"STX2ActivateShaker({self.device_ID},{shaker_id},{speed})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    def deactivate_shaker(self, shaker_id: int = 1) -> None:
        """
        Deactivates the specified shaker.
        Blank feedback response expected.

        Args:
            shaker_id (int): shaker iD (1 or 2).
        """
        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Deactivating shaker")
            command = f"STX2DeactivateShaker({self.device_ID},{shaker_id})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    def read_set_shaker_speed(self, shaker_id: int = 1) -> int:
        """
        Reads the set speed of the specified shaker.

        Args:
            shaker_id (int): shaker iD (1 or 2).

        Returns:
            int: The set speed of the specified shaker in rpm. Returns -1 if error.
        """
        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Reading set shaker speed")
            command = f"STX2ReadSetShakerSpeed({self.device_ID},{shaker_id})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")
            return int(feedback)

    def set_shaker_speed(self, shaker_id: int = 1, speed: int = 20) -> None:
        """
        Sets the speed of the specified shaker without starting the shaker.
        Blank feedback response expected.
        TODO: this method seems redundant with activate_shaker?

        Args:
            shaker_id (int): shaker iD (1 or 2).
            speed (int): Shaker speed in rpm (0-50).
        """
        if shaker_id not in [1, 2]:
            raise ValueError("shaker_id must be 1 or 2.")
        if speed < 1 or speed > 50:
            raise ValueError("speed must be between 1 and 50 rpm.")

        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Setting shaker speed")
            command = f"STX2SetShakerSpeed({self.device_ID},{shaker_id},{speed})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    # LOAD AND UNLOAD METHODS
    def load_plate(self, stack: int, slot: int) -> int:
        """
        Loads a plate into the specified slot.

        Args:
            stack (int): Stack number. NOTE: LiCONiC calls this slot
            slot (int): Slot number within the stack. NOTE: LiCONiC calls this level

        Returns:
            int: Feedback from the device.
                1 - plate has been loaded successfully
                -1 - previous long operation is not finished
                -2 - device is not initialized
                -3 - device has the Error status
                -4 - wrong value of a target position
                -5 - error loading a plate
        """
        with self.lock:
            self.logger.debug(
                f"{datetime.datetime.now()} - Loading plate into stack {stack}, slot {slot}"
            )
            command = f"STX2LoadPlate({self.device_ID},{stack},{slot})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")
            return feedback

    def unload_plate(self, stack: int, slot: int) -> int:
        """
        Unloads a plate from the specified slot.

        Args:
            stack (int): Stack number. NOTE: LiCONiC calls this slot
            slot (int): Slot number within the stack. NOTE: LiCONiC calls this level

        Returns:
            int: Feedback from the device.
                1 - plate has been unloaded successfully
                -1 - previous long operation is not finished
                -2 - device is not initialized
                -3 - device has the Error status
                -4 - wrong value of a target position
                -5 - error unloading a plate
        """
        with self.lock:
            self.logger.debug(
                f"{datetime.datetime.now()} - Unloading plate from stack {stack}, slot {slot}"
            )
            command = f"STX2UnloadPlate({self.device_ID},{stack},{slot})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")
            return feedback

    # SENSOR AND ERROR METHODS
    def read_transfer_station_detector(self) -> int:
        """
        Reads the status of the transfer station detector.

        Returns:
            int: Status of the transfer station detector.
                0 - no plate detected
                1 - plate detected
                -1 - error
        """
        with self.lock:
            self.logger.debug(
                f"{datetime.datetime.now()} - Reading transfer station detector"
            )
            command = f"STX2ReadXferStationDetector1({self.device_ID})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")
            return int(feedback)

    def beeper_off(self) -> None:
        """Turns off the beeper. Blank feedback response expected."""
        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Turning beeper off")
            command = f"STX2BeeperOff({self.device_ID})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")

    def get_system_status(self) -> str:
        """
        Gets the system status of the StoreX incubator.

        Returns:
            str: The system status.  # TODO: a string???

        # TODO: figure out how to interpret the system status
        """
        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Getting system status")
            command = f"STX2GetSysStatus({self.device_ID})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")
            return feedback

    def read_error_code(self) -> int:
        """
        Reads the current error code from the StoreX incubator.

        Returns:
            int: The current error code. 0 if no error, -1 if error.
        """
        with self.lock:
            self.logger.debug(f"{datetime.datetime.now()} - Reading error code")
            command = f"STX2ReadErrorCode({self.device_ID})\r"
            self.c_socket.send(command.encode())
            feedback = self.c_socket.recv(1024).decode().strip()
            self.logger.debug(f"{datetime.datetime.now()} - Feedback: {feedback}")
            return int(feedback)

    @property
    def is_busy(self) -> bool:
        """Returns whether the incubator is busy.
        TODO: is there a way to ask the device if it is busy???"""
        return bool(self.lock.locked())


if __name__ == "__main__":
    # Argument parser so users can test interface directly
    argparser = argparse.ArgumentParser()
    argparser.add_argument(
        "--host",
        type=str,
        help="Host location for the StoreX TCP/IP driver",
        default="localhost",
    )
    argparser.add_argument(
        "--port",
        type=int,
        help="Port location for the StoreX TCP/IP driver",
        default=3333,
    )
    args = argparser.parse_args()
    host = args.host
    port = args.port

    try:
        # intitialize LiCONiC driver connection for direct testing
        liconic = LICONIC(host=host, port=port)
        print(f"LiCONiC incubator device connected: {host=}, {port=}")
    except Exception as e:
        print(f"Error connecting to LiCONiC incubator driver at {host=}, {port=}")
        raise e
