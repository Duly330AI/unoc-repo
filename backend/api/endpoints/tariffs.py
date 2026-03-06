from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from backend.api.schemas import TariffOut
from backend.db import get_session, init_db
from backend.models import Tariff

router = APIRouter(prefix="/tariffs", tags=["tariffs"])


def _validate_tariff_values(payload: dict) -> None:
    up = payload.get("max_up_mbps")
    down = payload.get("max_down_mbps")
    if up is not None and up < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="max_up_mbps must be >= 0"
        )
    if down is not None and down < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="max_down_mbps must be >= 0"
        )
    tech = payload.get("technology")
    if tech is not None and tech not in {t.value for t in Tariff.TariffTechnology}:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="technology must be one of GPON|AON or null",
        )


@router.post("", response_model=TariffOut, status_code=status.HTTP_201_CREATED)
def create_tariff(data: dict):  # type: ignore[no-untyped-def]
    init_db()
    with get_session() as session:
        _validate_tariff_values(data)
        name = data.get("name")
        if not name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="name is required"
            )
        # unique name check
        existing = session.exec(select(Tariff).where(Tariff.name == name)).first()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="TARIFF_NAME_EXISTS")
        t = Tariff(
            name=name,
            max_up_mbps=float(data.get("max_up_mbps", 0.0)),
            max_down_mbps=float(data.get("max_down_mbps", 0.0)),
            technology=(
                Tariff.TariffTechnology(data.get("technology"))  # type: ignore[attr-defined]
                if data.get("technology") is not None
                else None
            ),
        )
        session.add(t)
        session.commit()
        session.refresh(t)
        assert t.id is not None
        return TariffOut(
            id=t.id,
            name=t.name,
            max_up_mbps=t.max_up_mbps,
            max_down_mbps=t.max_down_mbps,
            technology=(t.technology.value if t.technology is not None else None),
        )


@router.get("", response_model=list[TariffOut])
def list_tariffs():  # type: ignore[no-untyped-def]
    init_db()
    with get_session() as session:
        rows = session.exec(select(Tariff).order_by(Tariff.name)).all()
        out: list[TariffOut] = []
        for r in rows:
            assert r.id is not None
            out.append(
                TariffOut(
                    id=r.id,
                    name=r.name,
                    max_up_mbps=r.max_up_mbps,
                    max_down_mbps=r.max_down_mbps,
                    technology=(r.technology.value if r.technology is not None else None),
                )
            )
        return out


@router.get("/{tariff_id}", response_model=TariffOut)
def get_tariff(tariff_id: int):  # type: ignore[no-untyped-def]
    init_db()
    with get_session() as session:
        t = session.get(Tariff, tariff_id)
        if not t:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TARIFF_NOT_FOUND")
        assert t.id is not None
        return TariffOut(
            id=t.id,
            name=t.name,
            max_up_mbps=t.max_up_mbps,
            max_down_mbps=t.max_down_mbps,
            technology=(t.technology.value if t.technology is not None else None),
        )


@router.put("/{tariff_id}", response_model=TariffOut)
def update_tariff(tariff_id: int, data: dict):  # type: ignore[no-untyped-def]
    init_db()
    _validate_tariff_values(data)
    with get_session() as session:
        t = session.get(Tariff, tariff_id)
        if not t:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TARIFF_NOT_FOUND")
        # If name changes, enforce uniqueness
        new_name = data.get("name", t.name)
        if new_name != t.name:
            conflict = session.exec(select(Tariff).where(Tariff.name == new_name)).first()
            if conflict:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail="TARIFF_NAME_EXISTS"
                )
            t.name = new_name
        if "max_up_mbps" in data and data["max_up_mbps"] is not None:
            t.max_up_mbps = float(data["max_up_mbps"])
        if "max_down_mbps" in data and data["max_down_mbps"] is not None:
            t.max_down_mbps = float(data["max_down_mbps"])
        if "technology" in data:
            tech_val = data.get("technology")
            if tech_val is None:
                t.technology = None
            else:
                _validate_tariff_values({"technology": tech_val})
                t.technology = Tariff.TariffTechnology(tech_val)  # type: ignore[attr-defined]
        session.add(t)
        session.commit()
        session.refresh(t)
        assert t.id is not None
        return TariffOut(
            id=t.id,
            name=t.name,
            max_up_mbps=t.max_up_mbps,
            max_down_mbps=t.max_down_mbps,
            technology=(str(t.technology) if t.technology is not None else None),
        )


@router.delete("/{tariff_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tariff(tariff_id: int):  # type: ignore[no-untyped-def]
    init_db()
    with get_session() as session:
        t = session.get(Tariff, tariff_id)
        if not t:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="TARIFF_NOT_FOUND")
        session.delete(t)
        session.commit()
        return None
