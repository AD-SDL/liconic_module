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
class UnloadPlateModel(BaseModel):
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
    def validate_with_resource_tracker(self) -> "UnloadPlateModel":

        # 1. Ensure resource_tracker is provided
        if not self.resource_tracker:
            raise ValueError("resource_tracker must be provided for UnloadPlateModel validation")
        
        # Validate combination of inputs
        # TODO: check that this could not just be if not self.plate_id ...
        if not (self.plate_id and str(self.plate_id).lower() != "none") and not (self.stack and self.slot):
            raise ValueError("plate_id or both stack and slot must be provided")
        
        if self.stack and self.slot:
            # if stack/slot provided, validate combination
            if not self.resource_tracker.is_valid_stack_slot(self.stack, self.slot):
                raise ValueError(f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}")

        # if plate_id is provided, find stack/slot
        found_stack = None
        found_slot = None
        if self.plate_id and str(self.plate_id).lower() != "none":
            try: 
                found_stack, found_slot = self.resource_tracker.find_plate(str(self.plate_id))
            except Exception as e:
                raise ValueError(f"Error finding plate ID {self.plate_id}: {e}")
            
            # if stack/slot also provided, validate against found location
            if self.stack and self.slot:
                if not self.resource_tracker.is_valid_stack_slot(self.stack, self.slot):
                    raise ValueError(f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}")
                if found_stack != self.stack or found_slot != self.slot:
                    raise ValueError(f"Plate ID {self.plate_id} located at stack {found_stack}, slot {found_slot}, not user entered stack {self.stack}, slot {self.slot}")
                
            else:
                self.stack = found_stack
                self.slot = found_slot

        # TESTING if we reach here, we should have valid stack and slot values

        # check that location is occupied (in the case of no plate_id but stack/slot provided)
        if not self.resource_tracker.is_location_occupied(self.stack, self.slot):
            raise ValueError(f"No plate found at stack {self.stack}, slot {self.slot} to unload.")
        
        return self
    












