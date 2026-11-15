"""Research-only grid-scale energy-balance simulation. Positive kW means discharge.

Physical SOC is private to the plant and is never supplied to detection or policy.
The plant independently enforces hard SOC/power interlocks, thus zero violations
are BY CONSTRUCTION, not evidence of cyber-mitigation effectiveness.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class PlantConfig:
    capacity_kwh: float = 2000.0
    power_limit_kw: float = 1000.0
    soc_min: float = 20.0
    soc_max: float = 90.0
    initial_soc: float = 60.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    dt_minutes: float = 1.0

    def __post_init__(self):
        numeric = (self.capacity_kwh, self.power_limit_kw, self.soc_min, self.soc_max,
                   self.initial_soc, self.charge_efficiency, self.discharge_efficiency, self.dt_minutes)
        if not all(isfinite(v) for v in numeric):
            raise ValueError('Nonfinite grid-scale plant configuration')
        if not (self.capacity_kwh > 0 and self.power_limit_kw > 0 and self.dt_minutes > 0
                and 0 <= self.soc_min < self.initial_soc < self.soc_max <= 100
                and 0 < self.charge_efficiency <= 1 and 0 < self.discharge_efficiency <= 1):
            raise ValueError('Invalid grid-scale plant configuration')

class GridPlant:
    def __init__(self, cfg=None):
        self.cfg = cfg or PlantConfig()
        self._soc = self.cfg.initial_soc

    @property
    def evaluation_soc(self):
        """Evaluation/harness only. Never pass to Box 2 or Box 3."""
        return self._soc

    def step(self, requested_kw):
        if not isfinite(requested_kw):
            raise ValueError('Nonfinite plant power request')
        c = self.cfg
        h = c.dt_minutes / 60.0
        capped = max(-c.power_limit_kw, min(c.power_limit_kw, requested_kw))
        available_out_kwh = max(0.0, (self._soc-c.soc_min)/100*c.capacity_kwh)
        headroom_kwh = max(0.0, (c.soc_max-self._soc)/100*c.capacity_kwh)
        max_discharge_kw = available_out_kwh*c.discharge_efficiency/h
        max_charge_kw = headroom_kwh/(c.charge_efficiency*h)
        actual = min(capped,max_discharge_kw) if capped >= 0 else max(capped,-max_charge_kw)
        delta_kwh = (-actual/c.discharge_efficiency if actual >= 0
                     else -actual*c.charge_efficiency)*h
        self._soc += 100*delta_kwh/c.capacity_kwh
        self._soc = min(c.soc_max,max(c.soc_min,self._soc))
        return {'executed_kw': actual,
                'interlock_delta_kwh':abs(requested_kw-actual)*h,
                'soc_true_evaluation_only':self._soc}
