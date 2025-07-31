from typing import Union

def rangespace(start: Union[int, float], stop: Union[int, float], steps: int) -> list[int | float]:
    step_size = (stop - start) / steps
    return [start + (step_size * iteration) for iteration in range(steps + 1)]