"""Pydantic Models for validating LiCONiC MADSci Rest node action arguments."""

from typing import Any, Optional

from madsci.common.types.resource_types import Container
from pydantic import BaseModel, field_validator, model_validator


class LoadPlateModel(BaseModel):
    """Model for loading a plate into the LiCONiC incubator."""

    plate_type: str
    plate_id: Optional[str] = None
    stack: Optional[int] = None
    slot: Optional[int] = None
    resource_tracker: Any
    current_liconic_resource: Container

    @field_validator("stack")
    @classmethod
    def validate_stack(cls, v: Optional[int]) -> Optional[int]:
        """Validates the stack user input."""
        if v is not None and (v < 1 or v > 4):
            raise ValueError("stack must be between 1 and 4")
        return v

    @model_validator(mode="after")
    def validate_with_resource_tracker(self) -> "LoadPlateModel":
        """Validates the load plate model using the inventory handler."""

        # 1. Validate plate_type
        if not self.resource_tracker.is_valid_plate_type(self.plate_type):
            raise ValueError(f"Invalid plate type: {self.plate_type}")

        # 2. Validate stack/slot pairing.
        if bool(self.stack) ^ bool(self.slot):
            raise ValueError(
                "Both stack and slot must be specified when loading into a specific location."
            )

        # 3. If both stack and slot are provided, check that combination is valid.
        if self.stack and self.slot:
            # 3a. Check that the stack is valid for the specified plate type.
            valid_stacks = self.resource_tracker.find_valid_stack(
                plate_type=self.plate_type,
                current_liconic_resource=self.current_liconic_resource,
            )
            if self.stack not in valid_stacks:
                raise ValueError(
                    f"Stack {self.stack} not valid for plate type {self.plate_type}."
                )

            # 3b. Check that the stack/slot combination is valid
            if not self.resource_tracker.is_valid_stack_slot(
                self.stack,
                self.slot,
                self.current_liconic_resource,
            ):
                raise ValueError(
                    f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}."
                )

            # 3c. Check that the stack/slot location is not already occupied in the Resource Client.
            if self.resource_tracker.is_location_occupied(
                self.stack, self.slot, self.current_liconic_resource
            ):
                raise ValueError(
                    f"Location stack {self.stack}, slot {self.slot} already occupied."
                )

        # 4. Prevent duplicate plate ids
        if self.plate_id and str(self.plate_id).lower() != "none":
            try:
                self.resource_tracker.find_plate(
                    self.plate_id,
                    self.current_liconic_resource,
                )
            except ValueError:
                # If we get a ValueError, then no existing plate with the same ID was found. This is good.
                return self
            raise ValueError(f"Plate ID '{self.plate_id}' already exists")

        return self


class UnloadPlateModel(BaseModel):
    """Model for unloading a plate from the LiCONiC incubator."""

    plate_id: Optional[str] = None
    stack: Optional[int] = None
    slot: Optional[int] = None
    resource_tracker: Any
    current_liconic_resource: Container

    @field_validator("stack")
    @classmethod
    def validate_stack(cls, v: Optional[int]) -> Optional[int]:
        """Validates stack user entered argument."""
        if v is not None and (v < 1 or v > 4):
            raise ValueError("stack must be between 1 and 4")
        return v

    @model_validator(mode="after")
    def validate_with_resource_tracker(self) -> "UnloadPlateModel":
        """Validates the unload plate model using the Resource Client."""

        # 1. Validate combination of inputs.
        entered_plate_id = self.plate_id and str(self.plate_id).lower() != "none"
        entered_both_stack_and_slot = bool(self.stack) and bool(self.slot)
        if not (entered_plate_id or entered_both_stack_and_slot):
            raise ValueError("Plate ID or both stack and slot must be provided.")

        # 2. If stack and slot provided, validate the combination.
        if (self.stack and self.slot) and not self.resource_tracker.is_valid_stack_slot(
            stack=self.stack,
            slot=self.slot,
            current_liconic_resource=self.current_liconic_resource,
        ):
            raise ValueError(
                f"Invalid stack/slot combination: stack {self.stack}, slot {self.slot}."
            )

        # 3. If plate_id is provided, find the plate's stack/slot location.
        found_stack = None
        found_slot = None
        if self.plate_id and str(self.plate_id).lower() != "none":
            try:
                found_stack, found_slot = self.resource_tracker.find_plate(
                    plate_id=str(self.plate_id),
                    current_liconic_resource=self.current_liconic_resource,
                )
            except Exception as e:
                raise Exception(f"Error finding plate ID {self.plate_id}: {e}") from e

            # 3a. If stack/slot also provided, validate against found location
            if self.stack and self.slot:
                if found_stack != self.stack or found_slot != self.slot:
                    raise ValueError(
                        f"Plate ID {self.plate_id} located at stack {found_stack}, slot {found_slot}, not user entered stack {self.stack}, slot {self.slot}."
                    )

            else:
                self.stack = found_stack
                self.slot = found_slot

        # NOTE: At this point, we have either:
        #  a) found the stack/slot from plate_id
        #  b) validated the stack/slot provided

        # 4. Check that plate is located in stack/slot location in the Resource Client
        if not self.resource_tracker.is_location_occupied(
            stack=self.stack,
            slot=self.slot,
            current_liconic_resource=self.current_liconic_resource,
        ):
            raise ValueError(
                f"No plate found at stack {self.stack}, slot {self.slot} to unload."
            )

        return self


class BeginShakeModel(BaseModel):
    """Model for beginning a shake operation in the LiCONiC incubator."""

    shaker_id: Optional[int] = None
    shaker_speed: int

    @field_validator("shaker_id")
    @classmethod
    def validate_shaker_id(cls, v: Optional[int]) -> Optional[int]:
        """Validates the shaker_id argument."""
        if v not in [1, 2, None]:
            raise ValueError("shaker_id must be 1 or 2, or None for both shakers.")
        return v

    @field_validator("shaker_speed")
    @classmethod
    def validate_shaker_speed(cls, v: int) -> int:
        """Validates the shaker_speed argument."""
        if v < 1 or v > 50:
            raise ValueError("shaker_speed must be between 1 and 50.")
        return v


class EndShakeModel(BaseModel):
    """Model for ending a shake operation in the LiCONiC incubator."""

    shaker_id: Optional[int] = None

    @field_validator("shaker_id")
    @classmethod
    def validate_shaker_id(cls, v: Optional[int]) -> Optional[int]:
        """Validates the shaker_id argument."""
        if v not in [1, 2, None]:
            raise ValueError("shaker_id must be 1 or 2, or None for both shakers.")
        return v


class SetTemperatureModel(BaseModel):
    """Model for setting the target temperature of the LiCONiC incubator."""

    temperature: float

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validates the temperature argument."""
        if v < 4.0 or v > 50.0:
            raise ValueError(
                "temperature input must be in Celsius between 4.0 and 50.0."
            )
        return v


class SetHumidityModel(BaseModel):
    """Model for setting the target humidity of the LiCONiC incubator."""

    humidity: float

    @field_validator("humidity")
    @classmethod
    def validate_humidity(cls, v: float) -> float:
        """Validates the humidity argument."""
        if v < 0.0 or v > 95.0:
            raise ValueError("humidity input must be between 0.0 and 95.0 percent.")
        return v
