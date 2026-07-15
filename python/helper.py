import math

def get10percentList(maxVal: int = 60, expStep: float = 0.17, minVal: int = 1) -> int:
    values = []
    current = 1
    while current <= maxVal:
        values.append(str(current))
        step = max(minVal, math.floor(current * expStep))
        current += step

    return values
