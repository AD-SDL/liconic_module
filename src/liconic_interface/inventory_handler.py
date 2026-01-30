"""Provides a plate tracking class for managing the LiCONiC's storage"""

import datetime
from pathlib import Path
from typing import Any, Optional, Union

from defusedxml.ElementTree import parse
from madsci.client.resource_client import ResourceClient
from madsci.common.types.base_types import MadsciBaseModel as BaseModel
from madsci.common.types.resource_types import Resource
from pydantic import Field

from liconic_interface.labware_definitions import plate_definitions


class Slot(BaseModel):
    """Defines the structure of a slot"""

    occupied: bool = False
    plate_id: Optional[str] = None
    time_added: Optional[str] = None


class Stack(BaseModel):
    """Defines the structure of a stack"""

    slots: dict[int, Slot]

    def __init__(self, num_slots: int = 22, **data: Any) -> None:
        """Initializes the stack object"""
        if "slots" not in data:
            data["slots"] = {slot: Slot() for slot in range(1, num_slots + 1)}
        super().__init__(**data)

    def __getitem__(self, item: int) -> Slot:
        """Get a slot in the stack"""
        return self.slots[item]

    def __setitem__(self, key: int, value: Slot) -> None:
        """Set a slot in the stack"""
        self.slots[key] = value

    def __delitem__(self, key: int) -> None:
        """Delete a slot in the stack"""
        del self.slots[key]


class InventoryFile(BaseModel):
    """Defines the structure of the inventory file"""
    cassette_stacks: dict[int, int] = Field(
        default_factory=dict,
        exclude=True,
        repr=False,
    )
    stacks: dict[int, Stack] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Initializes the stacks based on cassette_stacks"""
        if self.stacks:
            return

        self.stacks = {
            stack_id: Stack(num_slots=levels)
            for stack_id, levels in self.cassette_stacks.items()
        }

    def __getitem__(self, item: int) -> Stack:
        """Get a stack in the inventory file"""
        return self.stacks[item]

    def __setitem__(self, key: int, value: Stack) -> None:
        """Set a stack in the inventory file"""
        self.stacks[key] = value

    def __delitem__(self, key: int) -> None:
        """Delete a stack in the inventory file"""
        del self.stacks[key]


class InventoryHandler:
    """Tracks the plate inventory of a LiCONiC incubator"""

    def __init__(
        self,
        cassette_config_path: Union[Path, str],
        module_inventory_file_path: Optional[Union[Path, str]] = None,
        resource_client: Optional[ResourceClient] = None,
        node_name: Optional[str] = None,
    ) -> None:
        """Initialize the inventory handler"""

        # Load labware definitions
        self.labware_definitions = plate_definitions
        self.cassette_config_path = Path(cassette_config_path).expanduser().resolve()
        self.stacks_dict = {}
        self.resource_client = resource_client
        self.node_name = node_name

        # parse the cassette config to determine stack sizes
        self.stacks_dict = self.parse_cassette_config(self.cassette_config_path)

        # Set up the inventory file path
        if not module_inventory_file_path:
            self.inventory_path = (
                Path.home() / ".madsci" / "liconic" / "liconic_inventory.yaml"
            )
        else:
            self.inventory_path = Path(module_inventory_file_path)

        # Load existing or create new inventory file
        if self.inventory_path.exists():
            self.inventory = InventoryFile.from_yaml(self.inventory_path)
        else:
            # create the file
            self.inventory_path.parent.mkdir(parents=True, exist_ok=True)

            # populate inventory file with empty stacks/slots
            self.inventory = InventoryFile(cassette_stacks=self.stacks_dict)
            self.update_inventory_file()


    def add_plate(
        self,
        plate_type: str,
        stack: int,
        slot: int,
        plate_id: Optional[str] = None,
        conveyor_child_resource: Optional[Resource] = None,
    ) -> None:
        """
        Updates the liconic inventory file when a new plate is placed into the incubator.

        Note: Some validations are included here for safety if this function is called directly.
        Args:
            plate_type (str): type of plate being added
            stack (int): stack number where plate is being added
            slot (int): slot number where plate is being added
            plate_id (Optional[str], optional): unique identifier for the plate. Defaults to None.
        Raises:
            ValueError: if plate type is unsupported
            ValueError: if stack is invalid for plate type
            ValueError: if stack/slot combination is invalid
            Exception: if location is already occupied

        """
        # Validations if function is called directly
        if not self.is_valid_plate_type(plate_type):
            raise ValueError(f"Unsupported plate type: {plate_type}")
        if stack not in self.find_valid_stack(plate_type):
            raise ValueError(f"Invalid stack {stack} for plate type {plate_type}")
        if not self.is_valid_stack_slot(stack, slot):
            raise ValueError(
                f"Invalid stack/slot combination: stack {stack}, slot {slot}"
            )
        if self.is_location_occupied(stack, slot):
            raise Exception("Location already occupied")

        # Add the plate to the inventory file
        self.inventory[stack][slot] = Slot(
            occupied=True,
            plate_id=plate_id,
            time_added=str(datetime.datetime.now()),
        )
        self.update_inventory_file()

        # Handle Resource Client calls
        # Collect conveyor plate resource, if available.
        conveyor_child_resource = self.resource_client.query_resource(resource_name=f"{self.node_name}_conveyor.nest").child
        # Push plate resource onto stack/slot nest resource
        stack_slot_resource = self.resource_client.query_resource(resource_name=f"{self.node_name}_stack{stack}_slot{slot}.nest")
        self.resource_client.push(resource=stack_slot_resource, child=conveyor_child_resource)


    def remove_plate(
        self,
        plate_id: Optional[str] = None,
        stack: Optional[int] = None,
        slot: Optional[int] = None,
    ) -> None:
        """
        Locates and removes the given plate from the inventory file

        Args:
            plate_type (str): type of plate being added
            stack (int): stack number where plate is being added
            slot (int): slot number where plate is being added

        # TODO: Remove duplicate checks!
        """
        # Check that user provided enough information
        if plate_id is None and stack is None and slot is None:
            raise ValueError(
                "Must specify plate_id or stack and slot to remove a plate"
            )
        if plate_id is None and (stack is None or slot is None):
            raise ValueError(
                "Must specify both stack and slot to remove a plate by location"
            )
        # Find plate if only plate_id is given
        if plate_id and (stack is None or slot is None):
            stack, slot = self.find_plate(plate_id)
        if not self.inventory[stack][slot].occupied:
            raise Exception("No plate in location")
        self.inventory[stack][slot] = Slot()
        self.update_inventory_file()

        # Handle resource client calls
        # Collect conveyor plate resource, if available.
        conveyor_resource = self.resource_client.query_resource(resource_name=f"{self.node_name}_conveyor.nest")
        if conveyor_resource.child:
            raise Exception("A child resource already exists on the conveyor nest.")
        # Collect plate resource at stack/slot nest
        stack_slot_resource_child = self.resource_client.query_resource(resource_name=f"{self.node_name}_stack{stack}_slot{slot}.nest").child
        if stack_slot_resource_child is None:
            raise Exception(f"No plate resource exists at {self.node_name}_stack{stack}_slot{slot}.nest to unload.")
        # Push plate resource onto conveyor resource
        self.resource_client.push(resource=conveyor_resource, child=stack_slot_resource_child)

    def find_plate(self, plate_id: str) -> tuple[int, int]:
        """
        Returns the stack and slot a plate is located on, given the plate id

        Args:
            plate_type (str):  name of the plate that matches existing plate definition

        Returns:
            tuple[int, int]: Tuple with the (stack, slot) location of the plate with the specified plate_id
        """
        for stack_key, stack in self.inventory.stacks.items():
            for slot_key, slot in stack.slots.items():
                if slot.plate_id == plate_id:
                    return stack_key, slot_key
        raise ValueError("Plate not found")

    def get_next_free_slot(self, plate_type: str) -> tuple[int, int]:
        """
        If no stack and shelf is passed into add_plate, return the next free location

        Args:
            plate_type (str):  name of the plate that matches existing plate definition

        Returns:
            tuple[int, int]: Tuple with a (stack, slot) combination of next available location

        Behavior:
           - all microplates ("flat_bottom_96well") will be loaded into stacks 1 and 2
           - all deepwell plates ("deep_96well") will be loaded into stacks 3 and 4
           - stacks will alternate between 1 and 2 (or 3 and 4) to balance shakers
        """

        candidate_stacks = self.find_valid_stack(plate_type)
        if candidate_stacks:
            # Get occupancy count for each stack in the group
            stack_occupancy = {}
            for stack_id in candidate_stacks:
                stack = self.inventory.stacks[(stack_id)]
                occupied_count = sum(
                    1 for slot in stack.slots.values() if slot.occupied
                )
                stack_occupancy[stack_id] = occupied_count

            # Pick the stack with fewer occupied slots (to balance load)
            # If tied, pick the lower-numbered stack
            stack_to_use = min(stack_occupancy, key=lambda s: (stack_occupancy[s], s))

            # Find the lowest-numbered free slot in that stack
            for slot_id_str, slot in sorted(
                self.inventory.stacks[(stack_to_use)].slots.items(),
                key=lambda x: int(x[0]),
            ):
                if not slot.occupied:
                    return stack_to_use, int(slot_id_str)

            # If the chosen stack is full, try the other one
            for alt_stack_id in candidate_stacks:
                if alt_stack_id == stack_to_use:
                    continue
                for slot_id_str, slot in sorted(
                    self.inventory.stacks[str(alt_stack_id)].slots.items(),
                    key=lambda x: int(x[0]),
                ):
                    if not slot.occupied:
                        return alt_stack_id, int(slot_id_str)

            raise Exception(f"No free slots available for plate type '{plate_type}'")
        raise Exception(f"No valid stacks found for plate type '{plate_type}'")

    def is_location_occupied(self, stack: int, slot: int) -> bool:
        """
        Given a stack and slot, determine if the location is occupied

        Args:
            stack (int): stack number in the incubator
            slot (int): slot number in the stack

        Returns:
            bool: True if location occupied, False otherwise

        """
        return self.inventory[int(stack)][int(slot)].occupied

    def get_plate_id(self, stack: int, slot: int) -> str:
        """
        Pull the plate id of the plate located in given stack and slot

        Args:
            stack (int): stack number in the incubator
            slot (int): slot number in the stack

        Returns:
            plate_id of plate at given stack/slot location
        """
        return self.inventory[int(stack)][int(slot)]["plate_id"]

    def update_inventory_file(self) -> None:
        """
        Updates the external inventory file to match self.inventory
        """
        self.inventory.to_yaml(self.inventory_path)

    def find_valid_stack(self, plate_type: str) -> list[int]:
        """
        Returns a list of valid stacks for the given plate type

        Args:
            plate_type (str): name of the plate that matches existing plate definition

        Returns:
            list[int] = list of stack numbers that are valid for the given plate type
        """
        valid_stacks = []
        if plate_type not in self.labware_definitions:
            raise ValueError(f"Unsupported plate type: {plate_type}")
        if plate_type == "flat_bottom_96well":
            valid_stacks = [1, 2]
        if plate_type == "deep_96well":
            valid_stacks = [3, 4]
        return valid_stacks

    def is_valid_plate_type(self, plate_type: str) -> bool:
        """Checks if plate type is valid based on labware definitions

        Args:
            plate_type (str): name of the plate that matches existing plate definition

        Returns:
            bool: True if plate type is valid, False otherwise
        """
        return plate_type in self.labware_definitions

    def is_valid_stack_slot(self, stack: int, slot: int) -> bool:
        """
        Checks if the given stack and slot are valid for the current configuration

        Args:
            stack (int): stack number in the incubator
            slot (int): slot number in the stack (numbered bottom to top)

        Returns:
            bool: True if stack/slot combination is valid for the current configuration, False otherwise
        """
        valid = True
        if stack not in self.inventory.stacks:
            valid = False
        if slot not in self.inventory[stack].slots:
            valid = False
        return valid


    def parse_cassette_config(self, cassette_config_path: Path) -> dict[int, int]:
        """
        Returns {cassette_id: levels}
        """
        tree = parse(cassette_config_path)
        root = tree.getroot()

        ns = {"ns": "http://com.liconic/cassettesconfig"}

        stacks: dict[int, int] = {}

        for cassette in root.findall("ns:Cassettes", ns):
            id_el = cassette.find("ns:Id", ns)
            levels_el = cassette.find("ns:Levels", ns)

            # Ignore range-based entries (Min/Max) for now
            if id_el is None or levels_el is None:
                continue

            stacks[int(id_el.text)] = int(levels_el.text)

        return stacks


if __name__ == "__main__":
    test = InventoryHandler()
