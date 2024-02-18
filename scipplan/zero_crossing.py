from dataclasses import field, dataclass
from textwrap import dedent

@dataclass
class ZeroCrossing:
    is_violated: bool = field(repr=False)
    iteration: int = None
    horizon: int = None
    start: float = None
    end: float = None
    dt_interval: float = None
    coef: float = field(init=False, default=None)
    new_dt_val: float = field(init=False, default=None)
    
    def __post_init__(self):
        if self.is_violated is True:
            if self.start is None or self.end is None or self.dt_interval is None:
                raise ValueError(
                    dedent(f"""
                    Incorrect input values, start, end and dt_interval have to be specified when zero crossing exists
                    
                    {self.start = }
                    {self.end = }
                    {self.dt_interval = }
                    """))
            avg_interval = (self.start + self.end) / 2.0
            self.coef = avg_interval / self.dt_interval
            self.new_dt_val = self.coef * self.dt_interval