from backend.services.layout_state import LAYOUT_STORE, LayoutPosition


def test_layout_patch_and_snapshot_versioning():
    # fresh store is global; snapshot version and positions
    v0, pos0 = LAYOUT_STORE.snapshot()
    # patch two positions
    v1 = LAYOUT_STORE.patch(
        [
            LayoutPosition(id="n1", x=1.0, y=2.0, userPinned=True),
            LayoutPosition(id="n2", x=-1.0, y=0.0, systemPinned=True),
        ]
    )
    assert v1 == v0 + 1
    # partial merge update
    v2 = LAYOUT_STORE.patch([LayoutPosition(id="n1", x=3.0, y=4.0)])
    assert v2 == v1 + 1
    _, snapshot = LAYOUT_STORE.snapshot()
    d = {p.id: p for p in snapshot}
    assert d["n1"].x == 3.0 and d["n1"].y == 4.0
    assert d["n1"].userPinned is True
    assert d["n2"].systemPinned is True
