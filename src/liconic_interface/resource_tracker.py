"""Provides a plate tracking class for managing the Liconic's storage"""

import datetime
from pathlib import Path
from typing import Optional, Union, Dict

from liconic_interface.labware_definitions import plate_definitions
from madsci.common.types.base_types import MadsciBaseModel as BaseModel

"""
TODO:
- add functionality to return elapsed time of plate storage
"""

class Slot(BaseModel):
    """Defines the structure of a slot"""

    occupied: bool = False
    plate_id: Optional[str] = None
    time_added: Optional[str] = None


class Stack(BaseModel):
    """Defines the structure of a stack"""
    slots: dict[int, Slot] = {}

    def __init__(self, num_slots: int = 22, **data) -> None:
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


class ResourceFile(BaseModel):
    """Defines the structure of the resource file"""
    stacks: dict[int, Stack] = {}   # TESTING PURPOSES

    def model_post_init(self, __context: any) -> None:
        if not self.stacks:
            self.stacks = {
                1: Stack(num_slots=22),
                2: Stack(num_slots=22),
                3: Stack(num_slots=10),
                4: Stack(num_slots=10),
            }

    def __getitem__(self, item: int) -> Stack:
        """Get a stack in the resource file"""
        return self.stacks[item]

    def __setitem__(self, key: int, value: Stack) -> None:
        """Set a stack in the resource file"""
        self.stacks[key] = value

    def __delitem__(self, key: int) -> None:
        """Delete a stack in the resource file"""
        del self.stacks[key]


class ResourceTracker:
    """Tracks the plate resources of a Liconic incubator"""

    def __init__(self, resource_path: Optional[Union[Path, str]] = None) -> None:
        """Initialize the resource tracker"""
        # Load labware definitions
        self.labware_definitions = plate_definitions   # TODO: be more consistent with naming!

        # Set up the resource file path
        if not resource_path:
            self.resource_path = (
                Path.home() / ".madsci" / "liconic" / "liconic_resources.yaml"
            )
        else:
            self.resource_path = Path(resource_path)
        if self.resource_path.exists():
            self.resources = ResourceFile.from_yaml(self.resource_path)
        else:
            self.resource_path.parent.mkdir(parents=True, exist_ok=True)
            self.resources = ResourceFile()
            self.update_resource_file()

    def add_plate(
        self,
        plate_type: str,
        stack: int,
        slot: int,
        plate_id: Optional[str] = None,
    ) -> None:
        """
        updates the liconic resource file when a new plate is placed into the liconic

        Note: some validations are included here for safety if this function is called directly.
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
        # Validations if funtion is called directly
        if not self.is_valid_plate_type(plate_type):
            raise ValueError(f"Unsupported plate type: {plate_type}")
        if not stack in self.find_valid_stack(plate_type):
            raise ValueError(f"Invalid stack {stack} for plate type {plate_type}")
        if not self.is_valid_stack_slot(stack, slot):
            raise ValueError(f"Invalid stack/slot combination: stack {stack}, slot {slot}")
        if self.is_location_occupied(stack, slot):
            raise Exception("Location already occupied")

        # Add the plate to the resource file
        self.resources[stack][slot] = Slot(
            occupied=True,
            plate_id=plate_id,
            time_added=str(datetime.datetime.now()),
        )
        self.update_resource_file()

    def remove_plate(
        self,
        plate_id: Optional[str] = None,
        stack: Optional[int] = None,
        slot: Optional[int] = None
    ) -> None:
        """
        locates and removes the given plate from the resource file
        """
        # check that user provided enough information
        if plate_id is None and stack is None and slot is None:
            raise ValueError("Must specify plate_id or stack and slot to remove a plate")
        if plate_id is None and (stack is None or slot is None):
            raise ValueError("Must specify both stack and slot to remove a plate by location")
        # find plate if only plate_id is given
        if plate_id and (stack is None or slot is None):
            stack, slot = self.find_plate(plate_id)
        if not self.resources[stack][slot].occupied:
            raise Exception("No plate in location")
        self.resources[stack][slot] = Slot()
        # TODO: get elapsed time of plate storage
        self.update_resource_file()

    def find_plate(self, plate_id: str) -> tuple[int, int]:
        """
        returns the stack and slot a plate is located on, given the plate id
        """
        for stack_key, stack in self.resources.stacks.items():
            for slot_key, slot in stack.slots.items():
                if slot.plate_id == plate_id:
                    return stack_key, slot_key
        raise ValueError("Plate not found")

    def get_next_free_slot(self, plate_type: str) -> tuple[int, int]:
        """
        if no stack and shelf is passed into add_plate, return the next free location

        Behavior:
           - all microplates ("flat_bottom_96well") will be loaded into stacks 1 and 2
           - all deepwell plates ("deep_96well") will be loaded into stacks 3 and 4

           stacks will alternate between 1 and 2 (or 3 and 4) to balance shakers
        """

        candidate_stacks = self.find_valid_stack(plate_type)
        if candidate_stacks:

            # Get occupancy count for each stack in the group
            stack_occupancy = {}
            for stack_id in candidate_stacks:
                stack = self.resources.stacks[(stack_id)]
                occupied_count = sum(1 for slot in stack.slots.values() if slot.occupied)
                stack_occupancy[stack_id] = occupied_count

            # Pick the stack with fewer occupied slots (to balance load)
            # If tied, pick the lower-numbered stack
            stack_to_use = min(stack_occupancy, key=lambda s: (stack_occupancy[s], s))

            # Find the lowest-numbered free slot in that stack
            for slot_id_str, slot in sorted(self.resources.stacks[(stack_to_use)].slots.items(), key=lambda x: int(x[0])):
                if not slot.occupied:
                    return stack_to_use, int(slot_id_str)

            # If the chosen stack is full, try the other one
            for alt_stack_id in candidate_stacks:
                if alt_stack_id == stack_to_use:
                    continue
                for slot_id_str, slot in sorted(self.resources.stacks[str(alt_stack_id)].slots.items(), key=lambda x: int(x[0])):
                    if not slot.occupied:
                        return alt_stack_id, int(slot_id_str)

            raise Exception(f"No free slots available for plate type '{plate_type}'")
        raise Exception(f"No valid stacks found for plate type '{plate_type}'")

    def is_location_occupied(self, stack: int, slot: int) -> bool:
        """
        given a stack and slot, determine if the location is occupied
        """
        return self.resources[int(stack)][int(slot)].occupied

    def get_plate_id(self, stack: int, slot: int) -> str:
        """
        pull the plate id of the plate located in given stack and slot
        """
        return self.resources[int(stack)][int(slot)]["plate_id"]

    def update_resource_file(self) -> None:
        """
        updates the external resource file to match self.resources
        """
        self.resources.to_yaml(self.resource_path)

    def find_valid_stack(self, plate_type: str) -> list[int]:
        """
        returns a list of valid stacks for the given plate type
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
        return plate_type in self.labware_definitions

    def is_valid_stack_slot(self, stack: int, slot: int) -> bool:
        """
        checks if the given stack and slot are valid for the current configuration
        """
        valid = True
        if stack not in self.resources.stacks:
            valid = False
        if slot not in self.resources[stack].slots:
            valid = False
        return valid

if __name__ == "__main__":
    test = ResourceTracker()