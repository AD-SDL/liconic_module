"""MADSci compatible REST Node for LiCONiC STX incubators"""

from typing import Any, Optional

from pydantic import BaseModel, field_validator, model_validator


class LoadPlateModel(BaseModel):
    """Model for loading a plate into the LiCONiC incubator"""

    plate_type: str
    plate_id: Optional[str] = None
    stack: Optional[int] = None
    slot: Optional[int] = None
    resource_tracker: Any = None

    def __init__(self, **data: Any) -> None:
        """Initializes the load plate model"""
        super().__init__(**data)

    @field_validator("stack")
    def validate_stack(cls, v: Optional[int]) -> Optional[int]:  # noqa: N805
        """Validates the stack user input"""
        if v is not None and (v < 1 or v > 4):
            raise ValueError("stack must be between 1 and 4")
        return v

    @model_validator(mode="after")
    def validate_with_resource_tracker(self) -> "LoadPlateModel":
        """Validates the load plate model using the resource tracker"""

        # 1. Validate plate_type
        if not self.resource_tracker.is_valid_plate_type(self.plate_type):
            raise ValueError(f"Invalid plate type: {self.plate_type})")

        # 2. Validate stack/slot pairing
        if bool(self.stack) ^ bool(self.slot):
            raise ValueError(
                "Must specify both stack and slot when loading into a specific location."
            )

        # 3. If stack and slot are provided, check that combination is valid
        if self.stack and self.slot:
            # 3a. Check that the stack is valid for the specified plate type
            valid_stacks = self.resource_tracker.find_valid_stack(
                plate_type=self.plate_type
            )
            if self.stack not in valid_stacks:
                raise ValueError(
                    f"Stack {self.stack} not valid for plate type {self.plate_type}"
                )
            # 3b. Check that the stack/slot combination is valid
            if not self.resource_tracker.is_valid_stack_slot(self.stack, self.slot):
                raise ValueError(
                    f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}"
                )
            # 3c. Check that the location is not already occupied
            if self.resource_tracker.is_location_occupied(self.stack, self.slot):
                raise ValueError(
                    f"Location stack {self.stack}, slot {self.slot} already occupied."
                )

        # 4. Prevent duplicate plate ids
        if self.plate_id and str(self.plate_id).lower() != "none":
            try:
                self.resource_tracker.find_plate(self.plate_id)
            except ValueError:
                # if we get a ValueError, then no existing plate with the same ID was found
                return self
            raise ValueError(f"Plate ID '{self.plate_id}' already exists")

        return self


class UnloadPlateModel(BaseModel):
    """Model for unloading a plate from the LiCONiC incubator"""

    plate_id: Optional[str] = None
    stack: Optional[int] = None
    slot: Optional[int] = None
    resource_tracker: Any = None

    def __init__(self, **data: Any) -> None:
        """Initializes the Unload Plate Pydantic Model"""
        super().__init__(**data)

    @field_validator("stack")
    def validate_stack(cls, v: Optional[int]) -> Optional[int]:  # noqa: N805
        """Validates stack user entered argument"""
        if v is not None and (v < 1 or v > 4):
            raise ValueError("stack must be between 1 and 4")
        return v

    @model_validator(mode="after")
    def validate_with_resource_tracker(self) -> "UnloadPlateModel":
        """Validates the unload plate model using the resource tracker"""

        # 1. Ensure resource_tracker is provided
        if not self.resource_tracker:
            raise ValueError(
                "resource_tracker must be provided for UnloadPlateModel validation"
            )

        # 2. Validate combination of inputs
        entered_plate_id = self.plate_id and str(self.plate_id).lower() != "none"
        entered_both_stack_and_slot = bool(self.stack) and bool(self.slot)
        if entered_plate_id or entered_both_stack_and_slot:
            pass
        else:
            raise ValueError("plate_id or both stack and slot must be provided")

        # 3. If stack/slot provided, validate combination
        if (self.stack and self.slot) and not self.resource_tracker.is_valid_stack_slot(
            self.stack, self.slot
        ):
            raise ValueError(
                f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}"
            )

        # 4. If plate_id is provided, find stack/slot
        found_stack = None
        found_slot = None
        if self.plate_id and str(self.plate_id).lower() != "none":
            try:
                found_stack, found_slot = self.resource_tracker.find_plate(
                    str(self.plate_id)
                )
            except Exception as e:
                raise Exception(f"Error finding plate ID {self.plate_id}: {e}") from e

            # 4a. If stack/slot also provided, validate against found location
            if self.stack and self.slot:
                if not self.resource_tracker.is_valid_stack_slot(self.stack, self.slot):
                    raise ValueError(
                        f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}"
                    )
                if found_stack != self.stack or found_slot != self.slot:
                    raise ValueError(
                        f"Plate ID {self.plate_id} located at stack {found_stack}, slot {found_slot}, not user entered stack {self.stack}, slot {self.slot}"
                    )

            else:
                self.stack = found_stack
                self.slot = found_slot

        """
        NOTE: At this point, we have either:
          a) found stack/slot from plate_id
          b) validated stack/slot provided
        """

        # 5. Check that plate is located in stack/slot location (in case where user provided stack/slot but not plate_id)
        if not self.resource_tracker.is_location_occupied(self.stack, self.slot):
            raise ValueError(
                f"No plate found at stack {self.stack}, slot {self.slot} to unload."
            )

        return self


class BeginShakeModel(BaseModel):
    """Model for beginning a shake operation in the LiCONiC incubator"""

    shaker_id: int | None
    shaker_speed: int

    @field_validator("shaker_id")
    def validate_shaker_id(cls, v: Optional[int]) -> Optional[int]:  # noqa: N805
        """Validates the shaker_id argument"""
        if v not in [1, 2, None]:
            raise ValueError("shaker_id must be 1 or 2, or None for both shakers")
        return v

    @field_validator("shaker_speed")
    def validate_shaker_speed(cls, v: Optional[int]) -> Optional[int]:  # noqa: N805
        """Validates the shaker_speed argument"""
        if v < 1 or v > 50:
            raise ValueError("shaker_speed must be between 1 and 50")
        return v


class EndShakeModel(BaseModel):
    """Model for ending a shake operation in the LiCONiC incubator"""

    shaker_id: int | None

    @field_validator("shaker_id")
    def validate_shaker_id(cls, v: Optional[int]) -> Optional[int]:  # noqa: N805
        """Validates the shaker_id argument"""
        if v not in [1, 2, None]:
            raise ValueError("shaker_id must be 1 or 2, or None for both shakers")
        return v


class SetTemperatureModel(BaseModel):
    """Model for setting the target temperature of the LiCONiC incubator"""

    temperature: float

    @field_validator("temperature")
    def validate_temperature(cls, v: Optional[float]) -> Optional[float]:  # noqa: N805
        """Validates the temperature argument"""
        if v < 4.0 or v > 50.0:
            raise ValueError("temperature must be in Celsius between 4.0 and 50.0")
        return v


class SetHumidityModel(BaseModel):
    """Model for setting the target humidity of the LiCONiC incubator"""

    humidity: float

    @field_validator("humidity")
    def validate_humidity(cls, v: Optional[float]) -> Optional[float]:  # noqa: N805
        """Validates the humidity argument"""
        if v < 0.0 or v > 95.0:
            raise ValueError("humidity must be between 0.0 and 95.0 percent")
        return v
