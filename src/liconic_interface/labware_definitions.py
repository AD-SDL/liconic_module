"""Labware definitions for use in the rapid350 MADSci workcell"""

from liconic_interface.resource_types import PlateResource

plate_definitions = {
    "microplate": PlateResource(
        plate_height=14,
        grip_height=1,
        plate_height_with_lid=16,
        lid_height=10,
        lid_grip_height=4,
        lid_removal_grip_height=12,
    ),
    "deep_well": PlateResource(
        plate_height=0,
        grip_height=0,
        plate_height_with_lid=0,
        lid_height=0,
        lid_grip_height=0,
        lid_removal_grip_height=0,
    ),
}
