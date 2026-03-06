from fastapi import APIRouter

from backend.constants import FIBER_TYPES

router = APIRouter(tags=["optical"], prefix="/optical")


@router.get("/fiber-types")
def get_fiber_types():
    """Return list of available fiber type keys and specs.

    Shape: { key, mode, standard, attenuation_db_per_km }
    """
    return [
        {
            "key": key,
            "mode": spec.mode,
            "standard": spec.standard,
            "attenuation_db_per_km": spec.attenuation_db_per_km,
        }
        for key, spec in FIBER_TYPES.items()
    ]


__all__ = ["router"]
