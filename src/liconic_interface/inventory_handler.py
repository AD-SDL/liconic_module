"""Provides a plate tracking class for managing the LiCONiC's storage"""

from pathlib import Path
from typing import Any, Optional, Union

from defusedxml.ElementTree import parse
from madsci.client.resource_client import ResourceClient
from madsci.common.types.base_types import MadsciBaseModel as BaseModel
from madsci.common.types.resource_types import Resource

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


# class InventoryFile(BaseModel):
#     """Defines the structure of the inventory file"""
#     cassette_stacks: dict[int, int] = Field(
#         default_factory=dict,
#         exclude=True,
#         repr=False,
#     )
#     stacks: dict[int, Stack] = Field(default_factory=dict)

#     def model_post_init(self, __context: Any) -> None:
#         """Initializes the stacks based on cassette_stacks"""
#         if self.stacks:
#             return

#         self.stacks = {
#             stack_id: Stack(num_slots=levels)
#             for stack_id, levels in self.cassette_stacks.items()
#         }

#     def __getitem__(self, item: int) -> Stack:
#         """Get a stack in the inventory file"""
#         return self.stacks[item]

#     def __setitem__(self, key: int, value: Stack) -> None:
#         """Set a stack in the inventory file"""
#         self.stacks[key] = value

#     def __delitem__(self, key: int) -> None:
#         """Delete a stack in the inventory file"""
#         del self.stacks[key]


class InventoryHandler:
    """Tracks the plate inventory of a LiCONiC incubator"""

    def __init__(
        self,
        cassette_config_path: Union[Path, str],
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

    def add_plate(
        self,
        plate_type: str,
        stack: int,
        slot: int,
        plate_id: Optional[str] = None,
        plate_resource: Resource = None,
        current_liconic_resource: Resource = None,
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
        if not self.is_valid_plate_type(plate_type):  # SHOULD STILL WORK
            raise ValueError(f"Unsupported plate type: {plate_type}")
        if stack not in self.find_valid_stack(
            plate_type=plate_type, current_liconic_resource=current_liconic_resource
        ):
            raise ValueError(f"Invalid stack {stack} for plate type {plate_type}")
        if not self.is_valid_stack_slot(
            stack=stack, slot=slot, current_liconic_resource=current_liconic_resource
        ):
            raise ValueError(
                f"Invalid stack/slot combination: stack {stack}, slot {slot}"
            )
        if self.is_location_occupied(
            stack=stack,
            slot=slot,
            current_liconic_resource=current_liconic_resource,
        ):
            raise Exception("Location already occupied")

        # Push plate resource onto stack/slot nest resource
        stack_resource = current_liconic_resource.children[str(stack)]
        slot_resource = stack_resource.children[str(slot)]
        self.resource_client.push(resource=slot_resource, child=plate_resource)

    def remove_plate(
        self,
        plate_id: Optional[str] = None,
        stack: Optional[int] = None,
        slot: Optional[int] = None,
        current_liconic_resource: Resource = None,
    ) -> None:
        """
        Locates and removes the given plate from the inventory file

        Args:
            plate_type (str): type of plate being added
            stack (int): stack number where plate is being added
            slot (int): slot number where plate is being added
            current_liconic_resource (Resource): Current state of the liconic container resource in MADSci Resource Client.

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
            stack, slot = self.find_plate(
                plate_id=plate_id, current_liconic_resource=current_liconic_resource
            )

        # check that there is a plate in that location:
        if not self.is_location_occupied(
            stack=stack,
            slot=slot,
            current_liconic_resource=current_liconic_resource,
        ):
            raise Exception(f"No plate resource in location stack {stack}, slot {slot}")
        stack_resource = current_liconic_resource.children[str(stack)]
        slot_resource = stack_resource.children[str(slot)]
        plate_resource = slot_resource.child

        # Ensure no plate resource already exists on conveyor nest
        # Collect conveyor plate resource, if available.
        conveyor_resource = self.resource_client.query_resource(
            resource_name=f"{self.node_name}_conveyor.nest"
        )
        if conveyor_resource.child:
            raise Exception("A child resource already exists on the conveyor nest.")

        # push plate resource onto conveyor resource
        self.resource_client.push(resource=conveyor_resource, child=plate_resource)

    def find_plate(
        self,
        plate_id: str,
        current_liconic_resource: Resource,
    ) -> tuple[int, int]:
        """
        Returns the stack and slot a plate is located on, given the plate id

        Args:
            plate_type (str):  name of the plate that matches existing plate definition
            current_liconic_resource (Resource): MADSci Resource object representing the current state of the incubator.

        Returns:
            tuple[int, int]: Tuple with the (stack, slot) location of the plate with the specified plate_id
        """
        # TODO: TEST THIS ONce A PLATE WITH A PLATE ID IS ADDED
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
        raise ValueError("Plate not found")

    def get_next_free_slot(
        self,
        plate_type: str,
        current_liconic_resource: Resource,
    ) -> tuple[int, int]:
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

        candidate_stacks = self.find_valid_stack(
            plate_type=plate_type,
            current_liconic_resource=current_liconic_resource,
        )
        # TESTING
        print(f"candiadate stacks: {candidate_stacks}")

        if candidate_stacks:
            # Get occupancy count for each stack in the group
            stack_occupancy = {}

            any_free_slot = False
            for stack_num in candidate_stacks:
                print(f"{stack_num=}")
                stack_resource = current_liconic_resource.children[str(stack_num)]
                capacity = stack_resource.capacity
                print(f"{capacity=}")
                occupancy_count = 0
                first_free_slot = None
                # for slot_num in stack_resource.children:
                for i in range(capacity):
                    slot_num = str(i + 1)
                    print(f"\t{slot_num=}")
                    slot_resource = stack_resource.children[slot_num]
                    occupied = len(slot_resource.children) == 1
                    print(f"\t{occupied=}")
                    if occupied:
                        occupancy_count += 1
                    elif first_free_slot is None:
                        first_free_slot = slot_num
                        any_free_slot = True

                stack_occupancy[stack_num] = (occupancy_count, first_free_slot)

            print("STACK OCCUPANCY")
            print(stack_occupancy)

            # Raise exception if there are no compatible slots available
            if any_free_slot is False:
                raise Exception(
                    f"No free slots available for plate type '{plate_type}'"
                )

            # Pick the stack with fewer occupied slots (to balance load)
            # If tied, pick the lower-numbered stack
            stack_to_use = min(
                stack_occupancy, key=lambda s: (stack_occupancy[s][0], s)
            )
            slot_to_use = int(stack_occupancy[stack_to_use][1])

            return stack_to_use, slot_to_use

        raise Exception(f"No valid stacks found for plate type '{plate_type}'")

    def is_location_occupied(
        self, stack: int, slot: int, current_liconic_resource: Resource
    ) -> bool:
        """
        Given a stack and slot, determine if the location is occupied

        Args:
            stack (int): stack number in the incubator
            slot (int): slot number in the stack
            current_liconic_resource: Resource object for the current incubator state

        Returns:
            bool: True if location occupied, False otherwise

        """
        stack_resource = current_liconic_resource.children[str(stack)]
        slot_resource = stack_resource.children[str(slot)]
        return len(slot_resource.children) == 1

    def find_valid_stack(
        self, plate_type: str, current_liconic_resource: Resource
    ) -> list[int]:
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
        attribute_to_search = ""
        if plate_type == "flat_bottom_96well":
            attribute_to_search = "microplate"
        elif plate_type == "deep_96well":
            attribute_to_search = "deep_well"

        for child in current_liconic_resource.children:
            if (
                current_liconic_resource.children[child].attributes["stack_type"]
                == attribute_to_search
            ):
                valid_stacks.append(int(child))
        return valid_stacks

    def is_valid_plate_type(self, plate_type: str) -> bool:
        """Checks if plate type is valid based on labware definitions

        Args:
            plate_type (str): name of the plate that matches existing plate definition

        Returns:
            bool: True if plate type is valid, False otherwise
        """
        return plate_type in self.labware_definitions

    def is_valid_stack_slot(
        self,
        stack: int,
        slot: int,
        current_liconic_resource: Resource,
    ) -> bool:
        """
        Checks if the given stack and slot are valid for the current configuration

        Args:
            stack (int): stack number in the incubator
            slot (int): slot number in the stack (numbered bottom to top)

        Returns:
            bool: True if stack/slot combination is valid for the current configuration, False otherwise
        """
        valid = True
        if str(stack) not in current_liconic_resource.children:
            valid = False
        if str(slot) not in current_liconic_resource.children[str(stack)].children:
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
