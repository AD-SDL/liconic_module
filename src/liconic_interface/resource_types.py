"""This module contains the Pydantic models for the PlateCrane resource types

NOTE: This is taken from the Hudson PlateCrane module in order to ensure plate type compatibility for now.
"""

from typing import Optional

from pydantic import BaseModel


class PlateResource(BaseModel):
    """A plate resource that can be manipulated by the PlateCrane EX"""

    # Plate Properties

    plate_height: float
    """The height measured from the bottom of the plate to the top"""
    grip_height: float
    """The height at which to grip the plate, measured from the bottom of the plate"""
    plate_height_with_lid: Optional[float] = None
    """The height of the plate when lidded, measured from the bottom of the plate to the top of the lid.
    Only required if the resource supports lids"""

    # Lid Properties

    lid_height: Optional[float] = None
    """The height of the lid alone, measured from the bottom of the lid to the top of the lid"""
    lid_grip_height: Optional[float] = None
    """The height at which to grip the lid itself, measured from the bottom of the lid"""
    lid_removal_grip_height: Optional[float] = None
    """The height at which to grip the lid when removing it, measured from the bottom of the lidded plate"""

    @staticmethod
    def convert_to_steps(plate_measurement_in_mm: float) -> int:
        """Converts plate measurements in mm to PlateCrane EX motor steps on the z-axis"""
        steps_per_mm = 80.5
        return int(plate_measurement_in_mm * steps_per_mm)
