"""Provides a plate tracking class for managing the Liconic's storage"""

import datetime
import random
from pathlib import Path

from madsci.common.types.base_types import BaseModel
from typing_extensions import Dict, Optional, Tuple, Union


class Slot(BaseModel):
    """Defines the structure of a slot"""

    occupied: bool = False
    plate_id: Optional[str] = None
    time_added: Optional[str] = None


class Stack(BaseModel):
    """Defines the structure of a stack"""

    slots: Dict[int, Slot] = {slot: Slot() for slot in range(1, 23)}

    def __getitem__(self, item):
        """Get a slot in the stack"""
        return self.slots[item]

    def __setitem__(self, key, value):
        """Set a slot in the stack"""
        self.slots[key] = value

    def __delitem__(self, key):
        """Delete a slot in the stack"""
        del self.slots[key]


class ResourceFile(BaseModel):
    """Defines the structure of the resource file"""

    stacks: Dict[int, Stack] = {stack: Stack() for stack in range(1, 5)}

    def __getitem__(self, item):
        """Get a stack in the resource file"""
        return self.stacks[item]

    def __setitem__(self, key, value):
        """Set a stack in the resource file"""
        self.stacks[key] = value

    def __delitem__(self, key):
        """Delete a stack in the resource file"""
        del self.stacks[key]


class ResourceTracker:
    """Tracks the plate resources of a Liconic incubator"""

    def __init__(self, resource_path: Optional[Union[Path, str]] = None):
        """Initialize the resource tracker"""
        if not resource_path:
            self.resource_path = (
                Path.home() / "liconic_temp/resources/liconic_resources.yaml"
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
        self, plate_id, stack=None, slot=None
    ):  # TODO: add parameter for identifying plate type if we have multiple types of stacks in liconic
        """
        updates the liconic resource file when a new plate is placed into the liconic
        """
        if stack is not None and slot is not None:
            if self.is_location_occupied(stack, slot):
                raise Exception("Location already occupied")
        else:
            stack, slot = self.get_next_free_slot()
        self.resources[stack][slot] = Slot(
            occupied=True,
            plate_id=plate_id,
            time_added=str(datetime.datetime.now()),
        )
        self.update_resource_file()

    def remove_plate(self, plate_id=None, stack=None, slot=None):
        """
        locates and removes the given plate from the resource file
        """
        if stack is None or slot is None:
            stack, slot = self.find_plate(plate_id)

        if not self.resources[stack][slot].occupied:
            raise Exception("No plate in location")
        else:
            self.resources[stack][slot] = Slot()
            # TODO: get elapsed time of plate storage
            self.update_resource_file()

    def find_plate(self, plate_id: str) -> Tuple[int, int]:
        """
        returns the stack and slot a plate is located on, given the plate id
        """
        for stack_key, stack in self.resources.stacks.items():
            for slot_key, slot in stack.slots.items():
                if slot.plate_id == plate_id:
                    return stack_key, slot_key
        raise Exception("Plate not found")

    def get_next_free_slot(self) -> Tuple[int, int]:
        """
        if no stack and shelf is passed into add_plate, return the next free location
        """
        stack_keys = list(self.resources.stacks.keys())
        random.shuffle(
            stack_keys
        )  # * randomize the order of the stacks to prevent the same stack from always being used
        for stack_key in stack_keys:
            for slot_key in self.resources[stack_key].slots.keys():
                if not self.resources[stack_key][slot_key].occupied:
                    return stack_key, slot_key
        raise Exception("No free slots available")

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
        self.resources.write_yaml(self.resource_path)


if __name__ == "__main__":
    test = ResourceTracker()
