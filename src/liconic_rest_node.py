"""REST-based client for the Liconic on Windows systems."""

import time
from pathlib import Path
from typing import Annotated, Optional

from madsci.common.types.action_types import ActionFailed
from madsci.common.types.node_types import RestNodeConfig
from madsci.common.types.resource_types import (
    Slot,
    Container,
)
from madsci.node_module.helpers import action
from madsci.node_module.rest_node_module import RestNode

from liconic_interface.inventory_handler import InventoryHandler
from liconic_interface.liconic_interface import LICONIC
from liconic_interface.pydantic_models import (
    BeginShakeModel,
    EndShakeModel,
    LoadPlateModel,
    SetHumidityModel,
    SetTemperatureModel,
    UnloadPlateModel,
)


class LiconicNodeConfig(RestNodeConfig):
    """Configuration for the LiCONiC REST node"""

    liconic_driver_port: int = 3333
    liconic_driver_host: str = "localhost"
    cassette_config_path: Path = Path(
        "C:/Liconic/stxdriver_64bit/DriverConfig/Devices/CassettesConfig1.xml"
    )
    module_inventory_file_path: Path = Path(
        Path.home() / ".madsci" / "liconic" / "liconic_resources.yaml"
    )
    node_definition: Path = Path("C:/Users/svcaibio/source/repos/liconic_module/definitions/liconic_lisa.node.yaml")
    # TODO: why does specifying node_definition path not work from the command line?

class LiconicRestNode(RestNode):
    """REST-based client for the LiCONiC incubator"""

    liconic_interface: LICONIC = None
    inventory_handler: InventoryHandler = None
    config: LiconicNodeConfig = LiconicNodeConfig()
    config_model = LiconicNodeConfig

    def startup_handler(self) -> None:
        """Called to (re)initialize the node. Should be used to open connections to devices or initialize any other resources."""

        # set up internal inventory handler (PARSES CASSETTE CONFIG AND LOADS/CREATES INVENTORY FILE)
        self.inventory_handler = InventoryHandler(
            self.config.cassette_config_path,
            self.config.module_inventory_file_path,
            self.resource_client,
            self.node_definition.node_name,
            )

        # create the resources
        self.init_resource_templates()
        self.create_resources()  # (CREATES MADSCI RESOURCES FROM CASSETTE DETAILS PARSED BY INVENTORY HANDLER)

        # initialize the node
        self.logger.log("Node initializing...")
        self.logger.log_info(
            f"Using host: {self.config.liconic_driver_host}, port: {self.config.liconic_driver_port}"
        )
        self.liconic_interface = LICONIC(
            self.config.liconic_driver_host, self.config.liconic_driver_port
        )

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
            self.logger.log_error(f"Error shutting down the LiCONiC Node: {err}")

    def init_resource_templates(self) -> None:
        """Initialize resource templates for the node module."""

        self.resource_client.create_template(
            resource=Slot(
                resource_description="The conveyor belt plate nest on the LiCONiC incubator",
            ),
            template_name="liconic_conveyor.nest",
            description="Template of a liconic conveyor nest",
            tags=["PlateNest", "ANSI/SLAS"],
        )

        # microplate slot template
        self.resource_client.create_template(
            resource=Slot(
                resource_description="Microplate nest template for inside LiCONiC incubator",
            ),
            template_name="liconic_microplate.nest",
            description="Template of a liconic microplate nest",
            tags=["PlateNest", "ANSI/SLAS", "microplate"],
        )

        # deep well slot template
        self.resource_client.create_template(
            resource=Slot(
                resource_description="Deep well nest template for inside LiCONiC incubator",
            ),
            template_name="liconic_deepwell.nest",
            description="Template of a liconic deepwell nest",
            tags=["PlateNest", "ANSI/SLAS", "deepwell", "microplate"],
        )

        # template for the entire liconic container
        self.resource_client.create_template(
            resource = Container(
                resource_description="Container for all LiCONiC incubator contents",
                capacity=4,  # can hold 4 stacks of any type
            ),
            template_name = "liconic_contents_container",
            description="Template for all incubator contents"
        )

        # microplate stack template
        self.resource_client.create_template(
            resource=Container(
                resource_description="Microplate stack resource. Holds up to 22 microplates.",
                capacity=22,
                attributes={
                    "stack_type": "microplate",
                }
            ),
            template_name = "microplate_stack_template",
            description="Microplate stack template for the LiCONiC incubator.",
        )

        # deep well stack template
        self.resource_client.create_template(
            resource=Container(
                resource_description="Deep well stack resource. Holds up to 10 deep well plates.",
                capacity=10,
                attributes={
                    "stack_type": "deep_well",
                }
            ),
            template_name = "deep_well_stack_template",
            description="Deep well stack template for the LiCONiC incubator.",
        )

    def create_resources(self) -> None:
        """Create resources for the node module."""

        # create the conveyor belt plate nest resource
        self.plate_carrier = self.resource_client.create_resource_from_template(
            template_name="liconic_conveyor.nest",
            resource_name=f"{self.node_definition.node_name}_conveyor.nest",
        )

        # create container resource for all liconic contents
        self.liconic_container = self.resource_client.create_resource_from_template(
            template_name="liconic_contents_container",
            resource_name = "liconic_incubator"
        )

        # create stack and slot nest resources inside the incubator
        for stack in self.inventory_handler.stacks_dict:
            num_stack_nests = self.inventory_handler.stacks_dict[stack]
            stack_template_name = "deep_well_stack_template" if num_stack_nests == 10 else "microplate_stack_template"
            nest_type = "deep_well" if num_stack_nests == 10 else "microplate"

            print()  # TESTING
            print(f"STACK{stack}")   # TESTING
            current_stack = self.resource_client.create_resource_from_template(
                template_name=stack_template_name,
                resource_name=f"stack{stack}",
            )
            self.resource_client.set_child(
                resource=self.liconic_container,
                child=current_stack,
                key=stack-1,
            )

            for i in range(num_stack_nests):
                print(f"slot{i+1}")  # TESTING
                self.resource_client.set_child(
                    resource = current_stack,
                    child = Slot(
                        resource_name=f"slot{i+1}",
                        resource_description=f"stack{stack}_slot{i+1} nest resource in LiCONiC incubator",
                        attributes={
                            "slot_type": nest_type
                        }
                    ),
                    key = i
                )
                time.sleep(0.02)  # worst of all possible options
                # could turn off rate limiting for the resource manager.


            # THIS IS THE MOVE!
                # Case 1: there's no existing implementation (new node construct based on xml)
                    # create resource after initializing all resources

                # Case 2: Already exists
                    # Get the existing version and make changes to it.
                    # query the whole thing
                    # make changes locally
                    # push all back up with update

                # NOTE: You can treat the resource items as python objects
                    # parent.children.append()
                    # parent.child[0] = the child... etc.

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

            transfer_station_status = (
                self.liconic_interface.read_transfer_station_detector()
            )
            self.cached_transfer_station_occupied = transfer_station_status == 1
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
    def set_target_temp(
        self, temp: Annotated[float, "target temperature in celsius"]
    ) -> None:
        """Sets the target temperature of the incubator"""

        # Validate temperature argument with pydantic
        try:
            SetTemperatureModel(temperature=temp)
        except Exception as err:
            # Fail action, don't put device into error state
            self.logger.log_error(f"Error validating set_target_temp arguments: {err}")
            return ActionFailed(errors=str(err))

        # Set the target temperature
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
            return None

    @action(
        name="set_target_humidity",
        description="Set the target humidity of the incubator",
    )
    def set_target_humidity(
        self, humidity: Annotated[float, "target humidity"]
    ) -> None:
        """Sets the target humidity of the incubator"""

        # Validate humidity argument with pydantic
        try:
            SetHumidityModel(humidity=humidity)
        except Exception as err:
            # Fail action, don't put device into error state
            self.logger.log_error(
                f"Error validating set_target_humidity arguments: {err}"
            )
            return ActionFailed(errors=str(err))

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
            return None

    @action(
        name="begin_shake",
        description="Begin shaking the incubator at the specified speed",
    )
    def begin_shake(
        self,
        shaker_id: Annotated[
            Optional[int],
            "shaker id (shaker 1 = stacks 1 and 2, shaker 2 = stacks 3 and 4 , or None for both shakers)",
        ] = None,
        shaker_speed: Annotated[
            int, "shaker speed (1-50 valid, default 20 = 200rpm)"
        ] = 20,
    ) -> None:
        """Activate the shaker in the LiCONiC incubator at the specified shaker_speed'"""

        # Validate arguments with pydantic model
        try:
            BeginShakeModel(
                shaker_id=shaker_id,
                shaker_speed=shaker_speed,
            )
        except Exception as err:
            # Don't put device into error state if argument validation fails, just fail action
            self.logger.log_error(f"Error validating begin_shake arguments: {err}")
            return ActionFailed(errors=str(err))

        # Activate shaker(s)
        if shaker_id and str(shaker_id).lower() != "none":
            self.liconic_interface.activate_shaker(
                shaker_id=int(shaker_id), speed=shaker_speed
            )
            time.sleep(2)
        elif shaker_id is None or str(shaker_id).lower() == "none":
            # activate both shakers
            self.liconic_interface.activate_shaker(shaker_id=1, speed=shaker_speed)
            time.sleep(2)
            self.liconic_interface.activate_shaker(shaker_id=2, speed=shaker_speed)
            time.sleep(2)
        else:
            self.logger.log_error("Error starting shaker, invalid shaker id.")
            return ActionFailed(errors="Error starting shaker, invalid shaker id.")
        return None

    @action(name="end_shake", description="Stop shaking the incubator")
    def end_shake(
        self,
        shaker_id: Annotated[
            Optional[int],
            "shaker id (shaker 1 = stacks 1 and 2, shaker 2 = stacks 3 and 4 , or None for both shakers)",
        ] = None,
    ) -> None:
        """Stop the shaker in the LiCONiC incubator"""

        # Validate arguments with pydantic model
        try:
            EndShakeModel(
                shaker_id=shaker_id,
            )
        except Exception as err:
            # Fail action, don't put device into error state
            self.logger.log_error(f"Error validating end_shake arguments: {err}")
            return ActionFailed(errors=str(err))

        # Deactivate shaker(s)
        if shaker_id and str(shaker_id).lower() != "none":
            # deactivate specified shaker
            self.liconic_interface.deactivate_shaker(shaker_id=int(shaker_id))
            time.sleep(2)
        elif shaker_id is None or str(shaker_id).lower() == "none":
            # deactivate both shakers
            self.liconic_interface.deactivate_shaker(shaker_id=1)
            time.sleep(2)
            self.liconic_interface.deactivate_shaker(shaker_id=2)
            time.sleep(2)
        else:
            self.logger.log_error("Error stopping shaker, invalid shaker id.")
            return ActionFailed(errors="Error stopping shaker, invalid shaker id.")
        return None

    @action(name="load_plate", description="Load a plate into the incubator")
    def load_plate(
        self,
        plate_type: Annotated[
            str, "plate type (flat_bottom_96well, deep_96well, etc.)"
        ],
        plate_id: Annotated[Optional[str], "plate id"] = None,
        stack: Annotated[
            Optional[int], "stack number (1-4), must also specify slot"
        ] = None,
        slot: Annotated[
            Optional[int],
            "slot number (1-22 for stacks 1 and 2, 1-10 for stacks 3 and 4, must also specify stack)",
        ] = None,
    ) -> None:
        """Load a plate into the incubator"""

        # Validate arguments with pydantic model
        try:
            LoadPlateModel(
                plate_type=plate_type,
                plate_id=plate_id,
                stack=stack,
                slot=slot,
                resource_tracker=self.inventory_handler,
            )
        except Exception as err:
            # Don't put device into error state if argument validation fails, just fail action
            self.logger.log_error(f"Error validating load_plate arguments: {err}")
            return ActionFailed(errors=str(err))

        # Find next free slot if none specified
        if stack is None and slot is None:
            stack, slot = self.inventory_handler.get_next_free_slot(
                plate_type=plate_type
            )

        # Check if there's a plate in the transfer station
        if self.liconic_interface.read_transfer_station_detector() == 0:
            self.logger.log_error(
                "Load_plate command cannot be completed, no plate in transfer station."
            )
            return ActionFailed(
                "Load_plate command cannot be completed, no plate in transfer station"
            )

        # Load the plate
        self.liconic_interface.load_plate(stack=stack, slot=slot)
        while self.liconic_interface.is_busy:
            time.sleep(1)
        self.inventory_handler.add_plate(
            plate_id=plate_id,
            stack=stack,
            slot=slot,
            plate_type=plate_type,
        )
        self.logger.log_info(f"Plate loaded into LiCONiC stack {stack}, slot {slot}")
        return None



    @action(name="unload_plate", description="Unload a plate from the incubator")
    def unload_plate(
        self,
        plate_id: Annotated[Optional[str], "plate id"] = None,
        stack: Annotated[Optional[int], "stacker number (1-4)"] = None,
        slot: Annotated[
            Optional[int],
            "slot number (1-22 for stacks 1 and 2, 1-10 for stacks 3 and 4)",
        ] = None,
    ) -> None:
        """Unload a plate from the incubator"""

        # Validate arguments with pydantic model
        self.logger.info(
            f"Unload plate arguments before validation: plate_id={plate_id}, stack={stack}, slot={slot}"
        )
        try:
            model = UnloadPlateModel(
                plate_id=plate_id,
                stack=stack,
                slot=slot,
                resource_tracker=self.inventory_handler,
            )
            # Extract validated values
            plate_id = model.plate_id
            stack = model.stack
            slot = model.slot
        except Exception as err:
            # Don't put device into error state if argument validation fails, just fail action
            self.logger.log_error(f"Error validating unload_plate arguments: {err}")
            return ActionFailed(errors=str(err))

        # Ensure transfer station is clear
        if self.liconic_interface.read_transfer_station_detector() == 1:
            self.logger.log_error(
                "Transfer station occupied, please clear it before unloading."
            )
            return ActionFailed(
                errors="Transfer station occupied, please clear it before unloading."
            )

        # Unload the plate
        self.liconic_interface.unload_plate(stack=stack, slot=slot)
        while self.liconic_interface.is_busy:
            time.sleep(1)
        self.inventory_handler.remove_plate(stack=stack, slot=slot)
        self.logger.info(f"Plate unloaded from LiCONiC stack {stack}, slot {slot}")
        return None


if __name__ == "__main__":
    liconic_module = LiconicRestNode()
    liconic_module.start_node()
