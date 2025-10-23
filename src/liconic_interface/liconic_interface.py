"""Connects to the Liconic Windows driver for testing purposes."""

import time
import socket
import datetime


class LICONIC:
    """
    Python interface for control of the LiCONiC STX88 incubator
    """

    def __init__(
        self,
        port: int = 3333,
        host: str = "localhost",
    )-> socket.socket:
        """Creates LiCONiC interface and connects to the device."""
        self.port = port
        self.host = host
        self.device_ID = "STX"
        self.c_socket = None
        self.connect()


    def __del__(self) -> None:
        """Cleans up the LiCONiC interface."""
        self.disconnect()


    def connect(self) -> None:  # WORKING
        """Connects to the Liconic device and initializes it if necessary."""
        server_address = (self.host, self.port)
        c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        c_socket.connect(server_address)
        self.c_socket = c_socket
        print("Connected to Liconic")

    def disconnect(self) -> None:  # WORKING
        """Disconnects from the Liconic device."""
        if self.c_socket:
            self.c_socket.close()
            self.c_socket = None
            print("Disconnected from Liconic")

    def activate(self) -> None:   # NOT WORKING
        """Opens serial communication and initializes the StoreX incubator."""
        if self.c_socket:
            try:
                self.c_socket.settimeout(15)   # for testing
                print(f"{datetime.datetime.now()} - Initializing Liconic...")
                self.c_socket.send(f"STX2Activate({self.device_ID})\r".encode())

                # listen for feedback for 15 seconds
                feedback = self.c_socket.recv(1024).decode().strip()
                print(f"{datetime.datetime.now()} - Feedback: {feedback}")

            except Exception as e:
                print(f"Error activate Liconic: {e}")

    def deactivate(self) -> None:   # NOT WORKING
        """Closes serial communication with the StoreX incubator."""
        if self.c_socket:
            try:
                self.c_socket.settimeout(15)
                print(f"{datetime.datetime.now()} - Deactivating Liconic...")
                self.c_socket.send(f"STX2Deactivate({self.device_ID})\r".encode())

                # listen for feedback for 15 seconds
                feedback = self.c_socket.recv(1024).decode().strip()
                print(f"{datetime.datetime.now()} - Feedback: {feedback}")

            except Exception as e:
                print(f"Error deactivate Liconic: {e}")

    def read_actual_climate(self) -> None:   # NOT WORKING
        """Reads the actual climate data from the StoreX incubator."""
        if self.c_socket:
            try:
                self.c_socket.settimeout(15)
                print(f"{datetime.datetime.now()} - Reading actual climate...")
                self.c_socket.send(f"STX2ReadActualClimate({self.device_ID})\r".encode())

                # listen for feedback for 15 seconds
                feedback = self.c_socket.recv(1024).decode().strip()
                print(f"{datetime.datetime.now()} - Feedback: {feedback}")

            except Exception as e:
                print(f"Error reading actual climate from Liconic: {e}")


if __name__ == "__main__":
    liconic = LICONIC()

    # # TESTING PURPOSES ONLY
    time.sleep(2)
    liconic.activate()
    liconic.read_actual_climate()

