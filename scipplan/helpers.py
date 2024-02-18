import os
from typing import Generator

class InfeasibilityError(Exception):
    """Raise this error when there are no valid solutions for the given horizon"""

def iterate(start: float, stop: float, step: float = 1) -> Generator[float, None, None]:
    n = start
    while n <= stop:
        yield n
        n += step
        
        
def list_accessible_files(directory):
    try:
        files = os.listdir(directory)
        return files
    except FileNotFoundError:
        return []  # Return an empty list if the directory doesn't exist

