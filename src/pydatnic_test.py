from liconic_interface.pydantic_models import LoadPlateModel, UnloadPlateModel
from liconic_interface.resource_tracker import ResourceTracker
# from madsci.common.types.base_types import MadsciBaseModel as BaseModel
from pathlib import Path

resources_path: Path = (
    Path.home() / ".madsci" / "liconic" / "liconic_resources.yaml"
)
resource_tracker = ResourceTracker(resource_path=resources_path)

print(resource_tracker.is_valid_plate_type("flat_bottom_96well"))

# # # TEST
# LoadPlateModel(
#     plate_type="flat_bottom_96well",
#     plate_id="plate_001",
#     stack=2,
#     slot=22,
#     resource_tracker=resource_tracker,
# )

UnloadPlateModel(
    plate_id="test",
    stack=None,
    slot=None,
    resource_tracker=resource_tracker,
)

# model = LoadPlateModel.model_validate(
#     {
#         "plate_type": "flat_bottom_96well",
#         "plate_id": "plate_001",
#         "stack": 2,
#         "slot": 1
#     },
#     context={"resource_tracker": resource_tracker}  # Pass private info via context
# )
