"""Handles communications with the Resource Client to manage the inventory of the LiCONiC incubator."""

from pathlib import Path
from typing import Optional, Union

from defusedxml.ElementTree import parse
from madsci.client.event_client import EventClient
from madsci.client.resource_client import ResourceClient
from madsci.common.types.resource_types import Resource

from liconic_interface.labware_definitions import plate_definitions
from liconic_interface.pydantic_models import LoadPlateModel, UnloadPlateModel


class InventoryHandler:
    """Communicates with the Resource Client to track incubator inventory."""

    def __init__(
        self,
        cassette_config_path: Union[Path, str],
        resource_client: Optional[ResourceClient] = None,
        node_name: Optional[str] = None,
    ) -> None:
        """Initialize the inventory handler."""

        # Load labware definitions.
        self.labware_definitions = plate_definitions
        self.cassette_config_path = Path(cassette_config_path).expanduser().resolve()
        self.stacks_dict = {}
        self.resource_client = resource_client
        self.node_name = node_name

        # Initialize EventClient for logging
        self.logger = EventClient()

        # Parse the cassette config to determine stack sizes.
        self.stacks_dict = self.parse_cassette_config(self.cassette_config_path)

    def add_plate(
        self,
        plate_type: str,
        stack: int,
        slot: int,
        plate_resource: Resource,
        current_liconic_resource: Resource,
        plate_id: Optional[str] = None,
        skip_validation: bool = False,
    ) -> None:
        """
        Updates the Resource Client when a plate is loaded into the incubator.

        Args:
            plate_type (str): Type of plate being added ("microplate" or "deep_well").
            stack (int): Stack number where plate is being added.
            slot (int): Slot number where plate is being added.
            plate_resource (Resource): MADSci resource object for the plate being added to the incubator.
            current_liconic_resource (Resource): MADSci Resource object representing the current state of the incubator.
            plate_id (str, optional): Unique identifier for the plate. Defaults to None.
            skip_validation (bool, optional): True to skip argument validations, False otherwise.
                NOTE: If this add_plate method is called from the load_plate action in the
                MADSci REST node, validation has already been completed and is not necessary.
        """
        if not skip_validation:
            try:
                LoadPlateModel(
                    plate_type=plate_type,
                    plate_id=plate_id,
                    stack=stack,
                    slot=slot,
                    current_liconic_resource=current_liconic_resource,
                    resource_tracker=self,
                )
            except Exception as err:
                self.logger.log_error(f"Error validating load_plate arguments: {err}")
                raise

        # Push plate resource onto stack/slot nest resource.
        stack_resource = current_liconic_resource.children[str(stack)]
        slot_resource = stack_resource.children[str(slot)]
        self.resource_client.push(resource=slot_resource, child=plate_resource)
        self.logger.log_info(
            f"Plate resource {plate_resource.resource_id} pushed into stack {stack}, slot {slot}."
        )

    def remove_plate(
        self,
        current_liconic_resource: Resource,
        plate_id: Optional[str] = None,
        stack: Optional[int] = None,
        slot: Optional[int] = None,
        skip_validation: bool = False,
    ) -> None:
        """
        Updates the Resource Client when a plate is unloaded from the incubator.

        Args:
            current_liconic_resource (Resource): MADSci Resource object representing the current state of the incubator.
            plate_id (str, optional): Unique identifier for the plate. Defaults to None.
            stack (int, optional): Stack number where plate is being added.
            slot (int, optional): Slot number where plate is being added.
            skip_validation (bool, optional): True to skip argument validations, False otherwise.
                NOTE: If this remove_plate method is called from the unload_plate action in the
                MADSci REST node, validation has already been completed and is not necessary.

        """
        if not skip_validation:
            try:
                # Validate arguments with a Pydantic model.
                model = UnloadPlateModel(
                    plate_id=plate_id,
                    stack=stack,
                    slot=slot,
                    resource_tracker=self,
                    current_liconic_resource=current_liconic_resource,
                )
                # Extract validated values
                plate_id = model.plate_id
                stack = model.stack
                slot = model.slot
            except Exception as err:
                self.logger.log_error(f"Error validating unload_plate arguments: {err}")
                raise

        # Ensure conveyor nest resource location is clear in Resource Client.
        conveyor_resource = self.resource_client.query_resource(
            resource_name=f"{self.node_name}_conveyor.nest"
        )
        if conveyor_resource.child:
            raise Exception("A child resource already exists on the conveyor nest.")

        # Collect the plate resource.
        stack_resource = current_liconic_resource.children[str(stack)]
        slot_resource = stack_resource.children[str(slot)]
        plate_resource = slot_resource.child

        # Push plate resource onto conveyor resource.
        self.resource_client.push(resource=conveyor_resource, child=plate_resource)
        self.logger.log_info(
            f"Plate resource {plate_resource.resource_id} pushed onto conveyor belt."
        )

    def find_plate(
        self,
        plate_id: str,
        current_liconic_resource: Resource,
    ) -> tuple[int, int]:
        """
        Returns the stack and slot location of a plate given the plate_id.

        Args:
            plate_id (str): Unique identifier for the plate.
            current_liconic_resource (Resource): MADSci Resource object representing the current state of the incubator.

        Returns:
            tuple[int, int]: Tuple with the (stack, slot) location of the plate with the specified plate_id.
        """
        located_stack = None
        located_slot = None
        for stack in current_liconic_resource.children:
            stack_resource = current_liconic_resource.children[stack]
            for slot in stack_resource.children:
                slot_resource = stack_resource.children[slot]
                if (len(slot_resource.children) == 1) and (
                    slot_resource.children[0].attributes["liconic_plate_id"] == plate_id
                ):
                    located_stack = int(stack)
                    located_slot = int(slot)
        if located_stack and located_slot:
            return (located_stack, located_slot)
        raise ValueError("Plate not found.")

    def get_next_free_slot(
        self,
        plate_type: str,
        current_liconic_resource: Resource,
    ) -> tuple[int, int]:
        """
        Returns the next free stack/slot location for a given plate type.

        Args:
            plate_type (str): Plate type (microplate or deep_well).
            current_liconic_resource (Resource): MADSci Resource object representing the current state of the incubator.

        Returns:
            tuple[int, int]: Tuple with a (stack, slot) combination of next available location.

        Behavior:
           - All "microplates" will be loaded into stacks with 22 slots (microplate compatible stacks).
           - All "deep_well" plates will be loaded into stacks with 10 slots (deep well compatible stacks).
           - Next available stack/slot location will alternate between compatible stacks to balance load.
           - The lowest available slot number will be chosen.
        """

        candidate_stacks = self.find_valid_stack(
            plate_type=plate_type,
            current_liconic_resource=current_liconic_resource,
        )

        if candidate_stacks:
            # Collect occupancy count and first free slot information for each valid stack.
            stack_occupancy = {}
            any_free_slot = False
            for stack_num in candidate_stacks:
                stack_resource = current_liconic_resource.children[str(stack_num)]
                capacity = stack_resource.capacity
                occupancy_count = 0
                first_free_slot = None
                for i in range(capacity):
                    slot_num = str(i + 1)
                    slot_resource = stack_resource.children[slot_num]
                    occupied = len(slot_resource.children) == 1
                    if occupied:
                        occupancy_count += 1
                    elif first_free_slot is None:
                        first_free_slot = slot_num
                        any_free_slot = True
                stack_occupancy[stack_num] = (occupancy_count, first_free_slot)

            # Raise exception if there are no compatible slots available.
            if not any_free_slot:
                raise Exception(
                    f"No free slots available for plate type '{plate_type}'."
                )

            # Pick the stack with fewer occupied slots (to balance load).
            # If tied, pick the lower-numbered stack.
            stack_to_use = min(
                stack_occupancy, key=lambda s: (stack_occupancy[s][0], s)
            )
            slot_to_use = int(stack_occupancy[stack_to_use][1])

            return stack_to_use, slot_to_use

        raise Exception(f"No valid stacks found for plate type '{plate_type}'.")

    def is_location_occupied(
        self, stack: int, slot: int, current_liconic_resource: Resource
    ) -> bool:
        """
        Determines if a stack/slot location is occupied in the Resource Client.

        Args:
            stack (int): Stack number in the incubator.
            slot (int): Slot number in the stack.
            current_liconic_resource (Resource): MADSci Resource object representing the current state of the incubator.

        Returns:
            bool: True if location occupied, False otherwise.

        """
        stack_resource = current_liconic_resource.children[str(stack)]
        slot_resource = stack_resource.children[str(slot)]
        return len(slot_resource.children) == 1

    def find_valid_stack(
        self, plate_type: str, current_liconic_resource: Resource
    ) -> list[int]:
        """
        Returns a list of valid stacks for the given plate type.

        Args:
            plate_type (str): Plate type (microplate or deep_well).
            current_liconic_resource (Resource): MADSci Resource object representing the current state of the incubator.

        Returns:
            list[int]: List of stack numbers that are valid for the given plate type.
        """
        valid_stacks = []
        if not self.is_valid_plate_type(plate_type=plate_type):
            raise ValueError(f"Unsupported plate type: {plate_type}.")
        for child in current_liconic_resource.children:
            if (
                current_liconic_resource.children[child].attributes["stack_type"]
                == plate_type
            ):
                valid_stacks.append(int(child))
        return valid_stacks

    def is_valid_plate_type(self, plate_type: str) -> bool:
        """Checks if plate type is valid based on labware definitions.

        Args:
            plate_type (str): Name of the plate that matches existing plate definition ("microplate" or "deep_well").

        Returns:
            bool: True if plate type is valid, False otherwise.
        """
        return plate_type in self.labware_definitions

    def is_valid_stack_slot(
        self,
        stack: int,
        slot: int,
        current_liconic_resource: Resource,
    ) -> bool:
        """
        Checks if the given stack/slot pair are valid for the current configuration.

        Args:
            stack (int): Stack number in the incubator.
            slot (int): Slot number in the stack (numbered bottom to top).
            current_liconic_resource (Resource): MADSci Resource object representing the current state of the incubator.

        Returns:
            bool: True if stack/slot combination is valid for the current configuration, False otherwise.
        """
        if str(stack) not in current_liconic_resource.children:
            return False
        return str(slot) in current_liconic_resource.children[str(stack)].children

    def parse_cassette_config(self, cassette_config_path: Path) -> dict[int, int]:
        """
        Returns a dictionary representing the current configuration of the incubator
        based on the CassetteConfig.xml file in the driver.

        Args:
            cassette_config_path (Path): Path to the cassette configuration XML file used by the driver.

        Returns:
            dict[int, int] = {
                stack number: number of slots in this stack,
                stack number: number of slots in this stack,
                ...,
            }

        """
        tree = parse(cassette_config_path)
        root = tree.getroot()

        ns = {"ns": "http://com.liconic/cassettesconfig"}

        stacks: dict[int, int] = {}

        for cassette in root.findall("ns:Cassettes", ns):
            id_el = cassette.find("ns:Id", ns)
            levels_el = cassette.find("ns:Levels", ns)

            # Ignore range-based entries (Min/Max) for now.
            if id_el is None or levels_el is None:
                continue

            stacks[int(id_el.text)] = int(levels_el.text)

        return stacks


if __name__ == "__main__":
    test = InventoryHandler()
