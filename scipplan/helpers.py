import os
import csv

from typing import Generator

from .config import Config

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

def write_to_csv(file_name: str, data: list[dict], config: Config) -> None:
    with open(f"{file_name}_{config.domain}_{config.instance}.csv", 'w', encoding='utf8', newline='') as output_file:
            fc = csv.DictWriter(output_file, 
                                fieldnames=data[0].keys(),
                            )
            fc.writeheader()
            fc.writerows(data)