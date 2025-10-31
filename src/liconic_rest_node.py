"""REST-based client for the Liconic on Windows systems."""

import time
import logging
from pathlib import Path
from typing import Annotated, Optional

from madsci.common.types.action_types import ActionFailed, ActionSucceeded
from madsci.common.types.node_types import RestNodeConfig
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from liconic_interface.liconic_interface import LICONIC
from liconic_interface.resource_tracker import ResourceTracker

from liconic_interface.pydantic_models import LoadPlateModel, UnloadPlateModel




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

    @action(
        name="set_target_temp",
        description="Set the target temperature of the incubator",
    )
    def set_target_temp(self, temp: Annotated[float, "target temperature"]):
        """Sets the target temperature of the incubator"""
        try:
            # get the current climate conditions
            climate = self.liconic_interface.read_set_climate()
            temp = float(temp)
            # set the new target temperature while keeping humidity, CO2, and N2 the same
            climate[0] = temp
            # set new climate with new temperature, making sure to preserve other values
            self.liconic_interface.write_set_climate(
                temperature=climate[0],
                humidity=climate[1],
                co2=climate[2],
                n2=climate[3],
            )
        except Exception as err:
            self.logger.log_error(f"Error setting target temperature: {err}")
            return ActionFailed(errors=str(err))
        else:
            self.logger.log("Target temperature set successfully.")
            return ActionSucceeded()

    @action(
        name="set_target_humidity",
        description="Set the target humidity of the incubator",
    )
    def set_target_humidity(self, humidity: Annotated[float, "target humidity"]):
        """Sets the target humidity of the incubator"""
        try:
            # get the current climate conditions
            climate = self.liconic_interface.read_set_climate()
            humidity = float(humidity)
            # set the new target humidity while keeping humidity, CO2, and N2 the same
            climate[1] = humidity
            # set new climate with new humidity, making sure to preserve other values
            self.liconic_interface.write_set_climate(
                temperature=climate[0],
                humidity=climate[1],
                co2=climate[2],
                n2=climate[3],
            )
        except Exception as err:
            self.logger.log_error(f"Error setting target humidity: {err}")
            return ActionFailed(errors=str(err))
        else:
            self.logger.log("Target humidity set successfully.")
            return ActionSucceeded()

    @action(
        name="begin_shake",
        description="Begin shaking the incubator at the specified speed",
    )
    def begin_shake(
        self,
        shaker_id: Annotated[Optional[int], "shaker id (shaker 1 = stacks 1 and 2, shaker 2 = stacks 3 and 4 , or None for both shakers)"] = None,
        shaker_speed: Annotated[int, "shaker speed (1-50 valid, default 20 = 200rpm)"] = 20
        ):
        """Activate the shaker in the liconic at the specified shaker_speed'"""

        # TODO: validate shaker inputs with pydantic...
            # TODO: remove validations from the driver??? or is it more safe to leave them in both places?

        try:
            # validate shaker speed
            shaker_speed = int(shaker_speed)
            if shaker_speed < 1 or shaker_speed > 50:
                raise ValueError("shaker_speed must be between 1 and 50.")
            # check if shaker_id is valid
            if shaker_id and str(shaker_id).lower() != "none":
                if int(shaker_id) not in [1, 2]:
                    raise ValueError("shaker_id, if specified, must be 1 or 2.")
                else:
                    self.liconic_interface.activate_shaker(shaker_id=int(shaker_id), speed=shaker_speed)
                    time.sleep(2)  # TODO: are these sleeps necessary?
            elif shaker_id is None or str(shaker_id).lower() == "none":
                # activate both shakers
                self.liconic_interface.activate_shaker(shaker_id=1, speed=shaker_speed)
                time.sleep(2) # TODO: are these sleeps necessary?
                self.liconic_interface.activate_shaker(shaker_id=2, speed=shaker_speed)
                time.sleep(2) # TODO: are these sleeps necessary?
            else:
                raise ValueError("Invalid shaker_id value.")
        except Exception as err:
            self.logger.log_error(f"Error starting shaker: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded()

    @action(name="end_shake", description="Stop shaking the incubator")
    def end_shake(
        self,
        shaker_id: Annotated[Optional[int], "shaker id (shaker 1 = stacks 1 and 2, shaker 2 = stacks 3 and 4 , or None for both shakers)"] = None):
        """Stop the shaker in the liconic"""
        try:
            # check if shaker_id is valid
            if shaker_id and str(shaker_id).lower() != "none":
                if int(shaker_id) not in [1, 2]:
                    raise ValueError("shaker_id, if spefified, must be 1 or 2.")
                else:
                    self.liconic_interface.deactivate_shaker(shaker_id=int(shaker_id))

            elif shaker_id is None or str(shaker_id).lower() == "none":
                # deactiavte both shakers
                self.liconic_interface.deactivate_shaker(shaker_id=1)
                self.liconic_interface.deactivate_shaker(shaker_id=2)

            else:
                raise ValueError("Invalid shaker_id value.")
        except Exception as err:
            self.logger.log_error(f"Error stopping shaker: {err}")
            return ActionFailed(errors=str(err))
        else:
            return ActionSucceeded()

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

        # Validate arguments with pydantic model
        try:
            self.logger.info(f"Resource tracker before LoadPlateModel: {self.module_resources}, type {type(self.module_resources)}")
            LoadPlateModel(
                plate_type=plate_type,
                plate_id=plate_id,
                stack=stack,
                slot=slot,
                resource_tracker=self.module_resources,
            )
        except Exception as err:
            # Don't put device into error state if argument validation fails, just fail action
            self.logger.log_error(f"Error validating load_plate arguments: {err}")
            return ActionFailed(errors=str(err))

        # Find next free slot if none specified
        if stack is None and slot is None:
            stack, slot = self.module_resources.get_next_free_slot(plate_type=plate_type)

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

        # Validate arguments with pydantic model
        try:
            self.logger.info(f"Resource tracker before LoadPlateModel: {self.module_resources}, type {type(self.module_resources)}")
            UnloadPlateModel(
                plate_id=plate_id,
                stack=stack,
                slot=slot,
                resource_tracker=self.module_resources,
            )
        except Exception as err:
            # Don't put device into error state if argument validation fails, just fail action
            self.logger.log_error(f"Error validating unload_plate arguments: {err}")
            return ActionFailed(errors=str(err))

        # TESTING
        self.logger.info(f"Unload plate arguments after validation: plate_id={plate_id}, stack={stack}, slot={slot}")

        # # helper function to log and return action failed
        # def action_failed(message: str) -> ActionFailed:
        #     self.logger.log_error(message)
        #     return ActionFailed(errors=message)

        # # Validations
        # if plate_id and str(plate_id).lower() != "none":
        #     self.logger.info(f"Input plate_id: {plate_id} ({type(plate_id)})")
        #     try:
        #         # 1. Attempt to find plate by id if provided
        #         found_stack, found_slot = self.module_resources.find_plate(str(plate_id))
        #         self.logger.info(f"Found plate ID {plate_id} at stack {found_stack}, slot {found_slot}")
        #         # 2. If stack and slot are also provided, validate against found location
        #         if stack and slot:
        #             self.logger.info(f"Input stack and slot: stack {stack} ({type(stack)}), slot {slot} ({type(slot)})")
        #             # 2. Validate stack/slot combo
        #             if self.module_resources.is_valid_stack_slot(stack, slot):
        #                 # 3. Check that the found location matches the specified location
        #                 if found_stack != stack or found_slot != slot:
        #                     return action_failed(f"Plate ID {plate_id} not located at specified stack {stack}, slot {slot}")
        #             else:
        #                 return action_failed(f"Invalid stack/slot combination: stack {stack}, slot {slot}")
        #         else:
        #             stack = found_stack
        #             slot = found_slot
        #     except ValueError as err:
        #         return action_failed(str(f"Error finding plate ID {plate_id}: {err}"))


        # # if we've gotten this far, either stack and slot were provided or found via plate id
        # # 4. Check that the location is actually occupied
        # if not self.module_resources.is_location_occupied(stack, slot):
        #     self.logger.log_error(f"No plate found at location stack {stack}, slot {slot}")
        #     return ActionFailed(errors=f"No plate found at location stack {stack}, slot {slot}")

        # 5. Check if transfer station is occupied, must be clear to unload
        if self.liconic_interface.read_transfer_station_detector() == 1:
            self.logger.log_error("Transfer station occupied, please clear it before unloading.")
            return ActionFailed(errors="Transfer station occupied, please clear it before unloading.")

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
