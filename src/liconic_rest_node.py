"""REST-based client for the Liconic"""

import time
from pathlib import Path
from typing import Optional

from madsci.client.resource_client import ResourceClient
from madsci.common.types.action_types import ActionFailed, ActionSucceeded
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode
from typing_extensions import Annotated

from liconic_interface import Stx
from liconic_interface.resource_tracker import ResourceTracker


class LiconicNodeConfig(RestNodeConfig):
    """Configuration for the Liconic REST node"""

    device: str = "/dev/ttyUSB0"
    resources_path: Path = Path.home() / "liconic_temp/resources/liconic_resources.yaml"


class LiconicRestNode(RestNode):
    """REST-based client for the Liconic incubator"""

    liconic_interface: Stx = None
    module_resources: ResourceTracker = None
    config_model = LiconicNodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        try:
            if self.config.resource_server_url:
                self.resource_client = ResourceClient(self.config.resource_server_url)
                self.resource_owner = OwnershipInfo(
                    node_id=self.node_definition.node_id
                )

            else:
                self.resource_client = None

            self.logger.log("Node initializing...")
            self.liconic_interface = Stx(self.config.device)
            self.resources_path = (
                Path(self.config.resources_path).expanduser().resolve()
            )
            self.module_resources = ResourceTracker(self.resources_path)

        except Exception as err:
            self.logger.log_error(f"Error starting the Liconic Node: {err}")
            self.startup_has_run = False
        else:
            self.startup_has_run = True
            self.logger.log("Liconic node initialized!")

    def shutdown_handler(self) -> None:
        """Called to shutdown the node. Should be used to close connections to devices or release any other resources."""
        try:
            self.logger.log("Shutting down")
            if self.liconic_interface is not None:
                self.shutdown_has_run = True
                del self.liconic_interface
                self.liconic_interface = None
                self.logger.log("Shutdown complete.")
        except Exception as err:
            self.logger.log_error(f"Error shutting down the Liconic Node: {err}")

    def state_handler(self) -> None:
        """Periodically called to update the current state of the node."""
        if self.liconic_interface is None:
            self.logger.log_error("Liconic interface is not initialized")
            return
        if self.liconic_interface.is_busy:
            self.node_state = {
                "liconic_status_code": "BUSY",
                "current_temperature": self.cached_current_temperature,
                "target_temperature": self.cached_target_temperature,
                "current_humidity": self.cached_current_humidity,
                "target_humidity": self.cached_target_humidity,
                "shovel_occupied": self.cached_shovel_occupied,
                "transfer_station_occupied": self.cached_transfer_station_occupied,
                "transfer_station_2_occupied": self.cached_transfer_station_2_occupied,
            }
            self.logger.info("BUSY")
        else:
            self.cached_current_temperature = self.liconic_interface.current_temperature
            self.cached_target_temperature = self.liconic_interface.target_temperature
            self.cached_current_humidity = self.liconic_interface.current_humidity
            self.cached_target_humidity = self.liconic_interface.target_humidity
            self.cached_shovel_occupied = self.liconic_interface.shovel_occupied
            self.cached_transfer_station_occupied = (
                self.liconic_interface.transfer_station_occupied
            )
            self.cached_transfer_station_2_occupied = (
                self.liconic_interface.transfer_station_2_occupied
            )
            self.node_state = {
                "liconic_status_code": "READY",
                "current_temperature": self.cached_current_temperature,
                "target_temperature": self.cached_target_temperature,
                "current_humidity": self.cached_current_humidity,
                "target_humidity": self.cached_target_humidity,
                "shovel_occupied": self.cached_shovel_occupied,
                "transfer_station_occupied": self.cached_transfer_station_occupied,
                "transfer_station_2_occupied": (
                    self.cached_transfer_station_2_occupied
                ),
            }
            self.logger.info("READY")

    @action(
        name="get_current_temp",
        description="Get the current temperature of the incubator",
    )
    def get_current_temp(self):
        """Returns the current temperature of the incubator"""
        try:
            current_temp = self.liconic_interface.current_temperature
        except Exception as err:
            self.logger.log_error(f"Error getting current temperature: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded(data={"current_temperature": current_temp})

    @action(
        name="get_target_temp",
        description="Get the target temperature of the incubator",
    )
    def get_target_temp(self):
        """Returns the target temperature of the incubator"""
        try:
            target_temp = self.liconic_interface.target_temperature
        except Exception as err:
            self.logger.log_error(f"Error getting target temperature: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded(data={"target_temperature": target_temp})

    @action(
        name="set_target_temp",
        description="Set the target temperature of the incubator",
    )
    def set_target_temp(self, temp: Annotated[float, "target temperature"]):
        """Sets the target temperature of the incubator"""
        try:
            self.liconic_interface.target_temperature = temp
        except Exception as err:
            self.logger.log_error(f"Error setting target temperature: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded()

    @action(
        name="get_current_humidity",
        description="Get the current humidity of the incubator",
    )
    def get_current_humidity(self):
        """Returns the current humidity of the incubator"""
        try:
            current_humidity = self.liconic_interface.current_humidity
        except Exception as err:
            self.logger.log_error(f"Error getting current humidity: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded(data={"current_humidity": current_humidity})

    @action(
        name="get_target_humidity",
        description="Get the target humidity of the incubator",
    )
    def get_target_humidity(self):
        """Returns the target humidity of the incubator"""
        try:
            target_humidity = self.liconic_interface.target_humidity
        except Exception as err:
            self.logger.log_error(f"Error getting target humidity: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded(data={"target_humidity": target_humidity})

    @action(
        name="set_target_humidity",
        description="Set the target humidity of the incubator",
    )
    def set_target_humidity(self, humidity: Annotated[float, "target humidity"]):
        """Sets the target humidity of the incubator"""
        try:
            self.liconic_interface.target_humidity = humidity
        except Exception as err:
            self.logger.log_error(f"Error setting target humidity: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded()

    @action(
        name="begin_shake",
        description="Begin shaking the incubator at the specified speed",
    )
    def begin_shake(self, shaker_speed: Annotated[int, "shaker speed"]):
        """Activate the shaker in the liconic at the specified 'shaker_speed'"""
        try:
            if not shaker_speed == self.liconic_interface.shaker_speed:
                """already shaking but not at the desired speed"""
                self.liconic_interface.shaker_active = False
                self.liconic_interface.shaker_speed = shaker_speed
                self.liconic_interface.shaker_active = True
        except Exception as err:
            self.logger.log_error(f"Error starting shaker: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded()

    @action(name="end_shake", description="Stop shaking the incubator")
    def end_shake(self):
        """Stop the shaker in the liconic"""
        try:
            self.liconic_interface.shaker_active = False
        except Exception as err:
            self.logger.log_error(f"Error stopping shaker: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded()

    @action(name="load_plate", description="Load a plate into the incubator")
    def load_plate(
        self,
        plate_id: Annotated[str, "plate id"],
        stacker: Annotated[Optional[int], "stacker number"] = None,
        slot: Annotated[Optional[int], "slot number"] = None,
    ):
        """Load a plate into the incubator"""
        if stacker is None or slot is None:
            stacker, slot = self.module_resources.get_next_free_slot()

        if self.module_resources.is_location_occupied(stacker, slot):
            self.logger.log_error(
                "load_plate command cannot be completed, already plate in given position"
            )
            return ActionFailed(
                errors="load_plate command cannot be completed, already plate in given position"
            )
        if not self.liconic_interface.transfer_station_occupied:
            self.logger.log_error(
                "load_plate command cannot be completed, no plate in transfer station"
            )
            return ActionFailed(
                errors="load_plate command cannot be completed, no plate in transfer station"
            )
        if plate_id is not None or plate_id != "":
            try:
                self.module_resources.find_plate(plate_id)
                self.logger.log_error(f"Plate with ID {plate_id} already in liconic")
                return ActionFailed(
                    errors=f"Plate with ID {plate_id} already in liconic"
                )
            except ValueError:
                pass
        self.liconic_interface.load_plate(stacker, slot)
        while self.liconic_interface.is_busy:
            time.sleep(1)
        self.module_resources.add_plate(plate_id, stacker, slot)
        return ActionSucceeded(
            data={"message": f"Plate loaded into liconic stack {stacker}, slot {slot}"}
        )

    @action(name="unload_plate", description="Unload a plate from the incubator")
    def unload_plate(
        self,
        plate_id: Annotated[Optional[str], "plate id"] = None,
        stacker: Annotated[Optional[int], "stacker number"] = None,
        slot: Annotated[Optional[int], "slot number"] = None,
    ):
        """Unload a plate from the incubator"""
        if stacker is None or slot is None and plate_id is not None:
            # * Get location based on plate id
            stacker, slot = self.module_resources.find_plate(plate_id)

        if self.liconic_interface.transfer_station_occupied:
            self.logger.log_error(
                "Transfer station occupied, please clear it before unloading."
            )
            return ActionFailed(
                errors="Transfer station occupied, please clear it before unloading."
            )
        if not self.module_resources.is_location_occupied(stacker, slot):
            if not self.liconic_interface.slot_occupied(stacker, slot):
                self.logger.log_error("No plate in location, can't unload.")
                return ActionFailed(errors="No plate in location, can't unload.")
        if plate_id is None:
            plate_id = self.module_resources.get_plate_id(stacker, slot)
        self.liconic_interface.unload_plate(stacker, slot)
        while self.liconic_interface.is_busy:
            time.sleep(1)
        if self.liconic_interface.transfer_station_occupied:
            self.module_resources.remove_plate(
                plate_id=plate_id, stack=stacker, slot=slot
            )
            return ActionSucceeded(
                data={
                    "message": f"Plate unloaded from liconic stack {stacker}, slot {slot}"
                }
            )
        else:
            self.logger.log_error("Failed to unload plate from liconic")
            return ActionFailed(
                errors=f"Failed to unload plate from liconic stack {stacker}, slot {slot}"
            )


if __name__ == "__main__":
    liconic_module = LiconicRestNode()
    liconic_module.start_node()
