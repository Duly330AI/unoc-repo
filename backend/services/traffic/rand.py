def _xorshift64star(x: int) -> int:
    x &= (1 << 64) - 1
    x ^= (x >> 12) & ((1 << 64) - 1)
    x ^= (x << 25) & ((1 << 64) - 1)
    x ^= (x >> 27) & ((1 << 64) - 1)
    return (x * 0x2545F4914F6CDD1D) & ((1 << 64) - 1)


def deterministic_rand01(base_seed: int, tick_seq: int, device_id: str) -> float:
    h = 0xCBF29CE484222325
    for ch in device_id.encode("utf-8"):
        h ^= ch
        h = (h * 0x100000001B3) & ((1 << 64) - 1)
    x = (base_seed & ((1 << 64) - 1)) ^ (tick_seq & ((1 << 64) - 1)) ^ h
    y = _xorshift64star(x)
    return (y >> 11) / float(1 << 53)
