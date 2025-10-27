from resource_types import PlateResource

# TODO: Add dimensions to the deep_96well!

# Dimensions of labware used on the BIO_Workcells
plate_definitions = {
    "flat_bottom_96well": PlateResource(
        plate_height=14,
        grip_height=1,
        plate_height_with_lid=16,
        lid_height=10,
        lid_grip_height=4,
        lid_removal_grip_height=12,
    ),
    "deep_96well": PlateResource(
        plate_height=0,
        grip_height=0,
        plate_height_with_lid=0,
        lid_height=0,
        lid_grip_height=0,
        lid_removal_grip_height=0,
    ),
    "tip_box_180uL": PlateResource(
        plate_height=0,
        grip_height=0,
        plate_height_with_lid=0,
        lid_height=0,
        lid_grip_height=0,
        lid_removal_grip_height=0,
    ),
    "pcr_96well": PlateResource(
        plate_height=0,
        grip_height=0,
        plate_height_with_lid=0,
        lid_height=0,
        lid_grip_height=0,
        lid_removal_grip_height=0,
    ),
}

