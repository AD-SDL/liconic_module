from pydantic import BaseModel, field_validator, model_validator, PrivateAttr
from typing import Optional, Any


class LoadPlateModel(BaseModel):
    plate_type: str
    plate_id: Optional[str] = None
    stack: Optional[int] = None
    slot: Optional[int] = None
    resource_tracker : Any = None

    def __init__(self, **data):
        super().__init__(**data)

    @field_validator("stack")
    def validate_stack(cls, v):
        if v is not None and (v < 1 or v > 4):
            raise ValueError("stack must be between 1 and 4")
        return v

    @model_validator(mode="after")
    def validate_with_resource_tracker(self):
        # 1. Validate plate_type
        if not self.resource_tracker.is_valid_plate_type(self.plate_type):
            raise ValueError(f"Invalid plate type: {self.plate_type})")

        # 2. Validate stack/slot pairing
        if bool(self.stack) ^ bool(self.slot):
            raise ValueError("Must specify both stack and slot when loading into a specific location.")

        # 3. If stack and slot are provided, check that combination is valid
        if self.stack and self.slot:
            # 3a. check that the stack is valid for the specified plate type
            valid_stacks = self.resource_tracker.find_valid_stack(plate_type=self.plate_type)
            if self.stack not in valid_stacks:
                raise ValueError(f"Stack {self.stack} not valid for plate type {self.plate_type}")
            # 3b. check that the stack/slot combination is valid
            if not self.resource_tracker.is_valid_stack_slot(self.stack, self.slot):
                raise ValueError(f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}")
            # 3c. check that the location is not already occupied
            if self.resource_tracker.is_location_occupied(self.stack, self.slot):
                raise ValueError(f"Location stack {self.stack}, slot {self.slot} already occupied.")

        # 4. Prevent duplicate plate ids
        if self.plate_id and str(self.plate_id).lower() != "none":
            try:
                self.resource_tracker.find_plate(self.plate_id)
            except ValueError:
                # if we get a ValueError, then no existing plate with the same ID was found
                return self
            raise ValueError(f"Plate ID '{self.plate_id}' already exists")

        return self

# TODO: continue testing!!!
# class UnloadPlateModel(BaseModel):
#     plate_id: Optional[str] = None
#     stack: Optional[int] = None
#     slot: Optional[int] = None
#     resource_tracker : Any = None

#     def __init__(self, **data):
#         super().__init__(**data)

#     @field_validator("stack")
#     def validate_stack(cls, v):
#         if v is not None and (v < 1 or v > 4):
#             raise ValueError("stack must be between 1 and 4")
#         return v

#     @model_validator(mode="after")
#     def validate_with_resource_tracker(self):

#         model = self.model_copy()

#         if self.plate_id and str(self.plate_id).lower() != "none":
#             try:
#                 # 1. Attempt to find plate by id if provided
#                 found_stack, found_slot = self.resource_tracker.find_plate(str(self.plate_id))
#                 print(f"Found plate ID {self.plate_id} at stack {found_stack}, slot {found_slot}")
#                 # 2. If stack and slot are also provided, validate against found location
#                 if self.stack and self.slot:
#                     print("hitting stack/slot validation")
#                     # 3. Validate stack/slot combo
#                     if self.resource_tracker.is_valid_stack_slot(self.stack, self.slot):
#                         # 4. Check that the found location matches the specified location
#                         if found_stack != self.stack or found_slot != self.slot:
#                             raise ValueError(f"Plate ID {self.plate_id} not located at specified stack {self.stack}, slot {self.slot}")
#                     else:
#                         raise ValueError(f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}")
#                 else:
#                     model.stack = found_stack
#                     model.slot = found_slot
#             except Exception as err:
#                 raise Exception(f"Error finding plate ID {self.plate_id}: {err}")

#         # returns valid stack/slot for unloading
#         return model
















        ##################################################################

        # 2. Validate stack/slot pairing
        if bool(self.stack) ^ bool(self.slot):
            raise ValueError("Must specify both stack and slot when loading into a specific location.")

        # 3. If stack and slot are provided, check that combination is valid
        if self.stack and self.slot:
            # 3a. check that the stack is valid for the specified plate type
            valid_stacks = self.resource_tracker.find_valid_stack(plate_type=self.plate_type)
            if self.stack not in valid_stacks:
                raise ValueError(f"Stack {self.stack} not valid for plate type {self.plate_type}")
            # 3b. check that the stack/slot combination is valid
            if not self.resource_tracker.is_valid_stack_slot(self.stack, self.slot):
                raise ValueError(f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}")
            # 3c. check that the location is not already occupied
            if self.resource_tracker.is_location_occupied(self.stack, self.slot):
                raise ValueError(f"Location stack {self.stack}, slot {self.slot} already occupied.")

        # 4. Prevent duplicate plate ids
        if self.plate_id and str(self.plate_id).lower() != "none":
            try:
                self.resource_tracker.find_plate(self.plate_id)
            except ValueError:
                # if we get a ValueError, then no existing plate with the same ID was found
                return self
            raise ValueError(f"Plate ID '{self.plate_id}' already exists")

        return self

