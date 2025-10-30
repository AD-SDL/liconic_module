"""REST-based client for the Liconic on Windows systems."""

import time
from pathlib import Path
from typing import Annotated, Optional

from madsci.common.types.action_types import ActionFailed, ActionSucceeded
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from liconic_interface.liconic_interface import LICONIC
from liconic_interface.resource_tracker import ResourceTracker


"""
TODOs:

- What's the best way to set node_url?
- Can arguments in the dashboard appear in the same order as code function arguments?
     - they seem to be alphabetical right now which is confusing
- Construct resource path from cassette config file!
    - FOR NOW!!! just edit existing file!  - DONE! (resource tracker edited to specify slot number per stack)
- test all load and unload argument combinations!
"""


class LiconicNodeConfig(RestNodeConfig):
    """Configuration for the Liconic REST node"""

    liconic_driver_port: int = 3333
    liconic_driver_host: str = "localhost"
    liconic_driver_cassette_config: str = "C:\\Liconic\\stxdriver_64bit\\DriverConfig\\Devices\\CassettesConfig1.xml"
    node_url: str = "http://hudson01.cels.anl.gov:2005" # generally don't want to do this. 
    # run as cli arg using --node_url http://hudson01.cels.anl.gov:2005
    

    # TODO: construct contents of this resource path from cassette config file
    resources_path: Path = (
        Path.home() / ".madsci" / "liconic" / "liconic_resources.yaml"
    )


class LiconicRestNode(RestNode):
    """REST-based client for the Liconic incubator"""

    liconic_interface: LICONIC = None
    module_resources: ResourceTracker = None
    config: LiconicNodeConfig = LiconicNodeConfig()
    config_model = LiconicNodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""
        self.logger.log("Node initializing...")
        self.logger.log_info(f"Using host: {self.config.liconic_driver_host}, port: {self.config.liconic_driver_port}")# TESTING
        self.liconic_interface = LICONIC(self.config.liconic_driver_host, self.config.liconic_driver_port)
        self.resources_path = Path(self.config.resources_path).expanduser().resolve()
        self.module_resources = ResourceTracker(self.resources_path)

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

    # TODO: re-implement state handler after testing!
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
                "transfer_station_occupied": self.cached_transfer_station_occupied,
            }
            self.logger.info("BUSY")
        else:
            # query device for temperature and humidity
            actual_climate = self.liconic_interface.read_actual_climate()
            self.cached_current_temperature = actual_climate[0]
            self.cached_current_humidity = actual_climate[1]
            target_climate = self.liconic_interface.read_set_climate()
            self.cached_target_temperature = target_climate[0]
            self.cached_target_humidity = target_climate[1]

            transfer_station_status = self.liconic_interface.read_transfer_station_detector()
            self.cached_transfer_station_occupied = True if transfer_station_status == 1 else False
            if transfer_station_status == -1:
                self.cached_transfer_station_occupied = "ERROR"

            self.node_state = {
                "liconic_status_code": "READY",
                "current_temperature": self.cached_current_temperature,
                "target_temperature": self.cached_target_temperature,
                "current_humidity": self.cached_current_humidity,
                "target_humidity": self.cached_target_humidity,
                "transfer_station_occupied": self.cached_transfer_station_occupied,
            }
            self.logger.info("READY")

    # TODO: TEST THIS!
    @action(
        name="set_target_temp",
        description="Set the target temperature of the incubator",
    )
    def set_target_temp(self, temp: Annotated[float, "target temperature"]):
        """Sets the target temperature of the incubator"""
        try:
            # get the current climate conditions
            climate = self.liconic_interface.read_set_climate()
            # set the new target temperature while keeping humidity, CO2, and N2 the same
            climate[0] = temp
            # set new climate with new temperature
            self.liconic_interface.set_climate(climate)
        except Exception as err:
            self.logger.log_error(f"Error setting target temperature: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded()

    # TODO: TEST THIS!
    @action(
        name="set_target_humidity",
        description="Set the target humidity of the incubator",
    )
    def set_target_humidity(self, humidity: Annotated[float, "target humidity"]):
        """Sets the target humidity of the incubator"""
        try:
            # get the current climate conditions
            climate = self.liconic_interface.read_set_climate()
            # set the new target humidity while keeping humidity, CO2, and N2 the same
            climate[1] = humidity
            # set new climate with new humidity
            self.liconic_interface.set_climate(climate)
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
            if (
                self.liconic_interface.shaker_active
                and shaker_speed != self.liconic_interface.shaker_speed
            ):
                """already shaking but not at the desired speed"""
                self.liconic_interface.shaker_active = False
                self.liconic_interface.shaker_speed = shaker_speed
                self.liconic_interface.shaker_active = True
                time.sleep(2)
            else:  # not shaking
                self.liconic_interface.shaker_speed = shaker_speed
                self.liconic_interface.shaker_active = True
                time.sleep(2)
        except Exception as err:
            self.logger.log_error(f"Error starting shaker: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded()

    # @action(name="end_shake", description="Stop shaking the incubator")
    # def end_shake(self):
    #     """Stop the shaker in the liconic"""
    #     try:
    #         self.liconic_interface.shaker_active = False
    #     except Exception as err:
    #         self.logger.log_error(f"Error stopping shaker: {err}")
    #         return ActionFailed(errors=str(err))
    #     else:
    #         return ActionSucceeded()

    # TODO: Add incubate action? Would we ever want to block for incubating on this large incubator?

    @action(name="load_plate", description="Load a plate into the incubator")
    def load_plate(
        self,
        plate_type: Annotated[str, "plate type (flat_bottom_96well, deep_96well, etc.)"],
        plate_id: Annotated[Optional[str], "plate id"] = None,
        stack: Annotated[Optional[int], "stack number (1-4), must also specify slot"] = None,
        slot: Annotated[Optional[int], "slot number (1-22 for stacks 1 and 2, 1-10 for stacks 3 and 4, must also specify stack)"] = None,
    ):
        """Load a plate into the incubator"""

        # define pydantic model 
        # then put arguments in the pydantic model

        # then you can continue with your funtion assuming you have valid arguments

        # helper function to log and return action failed
        def action_failed(message: str) -> ActionFailed:
            self.logger.log_error(message)
            return ActionFailed(errors=message)

        # Validations
        # 1. Validate plate type
        if not self.module_resources.is_valid_plate_type(plate_type):
            return action_failed(f"Invalid plate type: {plate_type}")

        # 2. Validate stack/slot pairing
        if bool(stack) ^ bool(slot):
            return action_failed("Must specify both stack and slot when loading into a specific location.")

        # 3. Validate stack & slot if provided
        if stack and slot:
            # 3a. check that the stack is valid for the specified plate type
            valid_stacks = self.module_resources.find_valid_stack(plate_type=plate_type)
            if stack not in valid_stacks:
                return action_failed(f"Stack {stack} not valid for plate type {plate_type}")
            # 3b. check that the stack/slot combination is valid
            if not self.module_resources.is_valid_stack_slot(stack, slot):
                return action_failed(f"Invalid stack/slot combination: stack {stack}, slot {slot}")
            # 3c. check that the location is not already occupied
            if self.module_resources.is_location_occupied(stack, slot):
                return action_failed(f"Location stack {stack}, slot {slot} already occupied.")

        # Find next free slot if none specified
        if stack is None and slot is None:
            stack, slot = self.module_resources.get_next_free_slot()

        # 4. Prevent duplicate plate ids
        if plate_id and str(plate_id).lower() != "none":
            try:
                self.module_resources.find_plate(plate_id)
                return action_failed(f"Plate with ID [{plate_id}] with type [{type(plate_id)}] already in liconic")
            except ValueError:
                # allow to continue if no duplicate plate ID
                pass

        # # 5. Check if there's a plate in the transfer station
        # # TODO: re-enable this check after testing!
        # if self.liconic_interface.read_transfer_station_detector() == 0:
        #     return action_failed(
        #         "Load_plate command cannot be completed, no plate in transfer station"
        #     )

        # Load the plate
        self.liconic_interface.load_plate(stack=stack,slot=slot)
        while self.liconic_interface.is_busy:
            time.sleep(1)
        self.module_resources.add_plate(
            plate_id=plate_id,
            stack=stack,
            slot=slot,
            plate_type=plate_type,
        )
        return ActionSucceeded(data={"message": f"Plate loaded into liconic stack {stack}, slot {slot}"})


    @action(name="unload_plate", description="Unload a plate from the incubator")
    def unload_plate(
        self,
        plate_id: Annotated[Optional[str], "plate id"] = None,
        stack: Annotated[Optional[int], "stacker number (1-4)"] = None,
        slot: Annotated[Optional[int], "slot number (1-22 for stacks 1 and 2, 1-10 for stacks 3 and 4)"] = None,
    ):
        """Unload a plate from the incubator"""

        # helper function to log and return action failed
        def action_failed(message: str) -> ActionFailed:
            self.logger.log_error(message)
            return ActionFailed(errors=message)

        # Validations
        if plate_id and str(plate_id).lower() != "none":
            try:
                # 1. Attempt to find plate by id if provided
                found_stack, found_slot = self.module_resources.find_plate(str(plate_id))
                if stack and slot:
                    # 2. Validate stack/slot combo - TODO: maybe unnecessary
                    if self.module_resources.is_valid_stack_slot(stack, slot):
                        # 3. Check that the found location matches the specified location
                        if found_stack != stack or found_slot != slot:
                            return action_failed(f"Plate ID {plate_id} not located at specified stack {stack}, slot {slot}")
                    else:
                        return action_failed(f"Invalid stack/slot combination: stack {stack}, slot {slot}")
            except ValueError as err:
                return action_failed(str(f"Error finding plate ID {plate_id}: {err}"))

        # if we've gotten this far, either stack and slot were provided or found via plate id
        # 4. Check that the location is actually occupied
        if not self.module_resources.is_location_occupied(stack, slot):
            return action_failed(f"No plate found at location stack {stack}, slot {slot}")

        # 5. Check if transfer station is occupied, must be clear to unload
        if self.liconic_interface.read_transfer_station_detector() == 1:
            return action_failed(
                "Transfer station occupied, please clear it before unloading."
            )

        # Unload the plate
        self.liconic_interface.unload_plate(stack=stack,slot=slot)
        while self.liconic_interface.is_busy:
            time.sleep(1)
        self.module_resources.remove_plate(stack=stack, slot=slot)
        return ActionSucceeded(
            data={"message": f"Plate unloaded from liconic stack {stack}, slot {slot}"}
        )

if __name__ == "__main__":
    liconic_module = LiconicRestNode()
    liconic_module.start_node()
