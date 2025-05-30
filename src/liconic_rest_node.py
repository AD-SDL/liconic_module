"""REST-based client for the Liconic"""
# ruff: noqa

import time
from pathlib import Path
from typing import Optional

from madsci.client.resource_client import ResourceClient
from madsci.common.types.auth_types import OwnershipInfo
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.rest_node_module import RestNode

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
    config_model: LiconicNodeConfig

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


# _#_#_#_#OLD_CODE_#_#_#_#_#


@liconic_module.action()
def get_current_temp(state: State) -> StepResponse:
    """Returns the current temperature of the incubator"""
    return StepResponse.step_succeeded(
        state.liconic.climate_controller.current_temperature
    )


@liconic_module.action()
def get_target_temp(state: State) -> StepResponse:
    """Returns the target temperature of the incubator"""
    return StepResponse.step_succeeded(
        state.liconic.climate_controller.target_temperature
    )


@liconic_module.action()
def set_target_temp(state: State, temp: float) -> StepResponse:
    """Sets the target temperature of the incubator"""
    liconic: Stx = state.liconic
    try:
        liconic.target_temperature = float(temp)
        return StepResponse.step_succeeded(f"Set temperature to {temp}")
    except ValueError:
        error_msg = "Error: temp argument must be a float"
        print(error_msg)
        return StepResponse.step_failed(error_msg)


@liconic_module.action()
def get_current_humidity(state: State) -> StepResponse:
    """Returns the current humidity of the incubator"""
    liconic: Stx = state.liconic
    return StepResponse.step_succeeded(liconic.current_humidity)


@liconic_module.action()
def get_target_humidity(state: State) -> StepResponse:
    """Returns the target humidity of the incubator"""
    liconic: Stx = state.liconic
    return StepResponse.step_succeeded(liconic.target_humidity)


@liconic_module.action()
def set_target_humidity(state: State, humidity: float) -> StepResponse:
    """Sets the target humidity of the incubator"""
    liconic: Stx = state.liconic
    liconic.target_humidity = float(humidity)
    return StepResponse.step_succeeded(f"Set humidity to {humidity}")


@liconic_module.action()
def begin_shake(state: State, shaker_speed: int):
    """Activate the shaker in the liconic at the specified 'shaker_speed'"""
    liconic: Stx = state.liconic
    if not shaker_speed == int(liconic.shaker_speed):
        """already shaking but not at the desired speed"""
        liconic.shaker_active = False
        liconic.shaker_speed = int(shaker_speed)
    liconic.shaker_active = True
    return StepResponse.step_succeeded(
        f"Liconic shaker activated, shaker speed: {liconic.shaker_speed}"
    )


@liconic_module.action()
def end_shake(state: State):
    """Stop the liconic's shaker"""
    liconic: Stx = state.liconic
    liconic.shaker_active = False
    return StepResponse.step_succeeded("Liconic shaker stopped")


@liconic_module.action()
def load_plate(
    state: State,
    plate_id: str,
    stacker: Optional[int] = None,
    slot: Optional[int] = None,
):
    """Load a plate into the incubator"""
    liconic: Stx = state.liconic
    module_resources: ResourceTracker = state.module_resources
    if stacker is None or slot is None:
        stacker, slot = module_resources.get_next_free_slot()
    else:
        stacker = int(stacker)
        slot = int(slot)
    if module_resources.is_location_occupied(stacker, slot):
        return StepResponse.step_failed(
            "load_plate command cannot be completed, already plate in given position"
        )
    if not liconic.transfer_station_occupied:
        return StepResponse.step_failed(
            "load_plate command cannot be completed, no plate in transfer station"
        )
    if plate_id is not None or plate_id != "":
        try:
            module_resources.find_plate(plate_id)
            return StepResponse.step_failed(
                f"Plate with ID {plate_id} already in liconic"
            )
        except ValueError:
            pass
    liconic.load_plate(stacker, slot)
    while liconic.is_busy:
        time.sleep(1)
    module_resources.add_plate(plate_id, stacker, slot)
    return StepResponse.step_succeeded(
        f"Plate loaded into liconic stack {stacker}, slot {slot}"
    )


@liconic_module.action()
def unload_plate(
    state: State,
    plate_id: Optional[str] = None,
    stacker: Optional[int] = None,
    slot: Optional[int] = None,
):
    """Unload a plate from the incubator"""
    liconic: Stx = state.liconic
    module_resources: ResourceTracker = state.module_resources
    if stacker is None or slot is None and plate_id is not None:
        # * Get location based on plate id
        stacker, slot = module_resources.find_plate(plate_id)
    else:
        stacker = int(stacker)
        slot = int(slot)
    if liconic.transfer_station_occupied:
        return StepResponse.step_failed(
            "Transfer station occupied, please clear it before unloading."
        )
    if not module_resources.is_location_occupied(stacker, slot):
        if not liconic.slot_occupied(stacker, slot):
            return StepResponse.step_failed("No plate in location, can't unload.")
    if plate_id is None:
        plate_id = module_resources.get_plate_id(stacker, slot)
    liconic.unload_plate(stacker, slot)
    while liconic.is_busy:
        time.sleep(1)
    if liconic.transfer_station_occupied:
        module_resources.remove_plate(plate_id=plate_id, stack=stacker, slot=slot)
        return StepResponse.step_succeeded(
            f"Plate unloaded from liconic stack {stacker}, slot {slot}"
        )
    else:
        print(f"Failed to unload plate from liconic stack {stacker}, slot {slot}")


if __name__ == "__main__":
    liconic_module.start()
