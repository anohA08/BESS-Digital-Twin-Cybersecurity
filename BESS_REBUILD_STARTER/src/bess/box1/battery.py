"""
battery.py

Battery model for the Grid-Scale BESS Digital Twin.

Features
--------
- Loads battery parameters from JSON
- Loads OCV lookup table
- Loads resistance lookup table
- Interpolates OCV and internal resistance using SOC
- Computes terminal voltage
- Supports charging and discharging
- Designed to be used later by BatteryPack
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd


class Battery:
    """Data-driven battery model based on the URI-PBEST dataset."""

    def __init__(self):

        # -------------------------------------------------
        # Locate processed data
        # -------------------------------------------------
        root = Path(__file__).parent
        processed = root / "data" / "processed"

        # -------------------------------------------------
        # Load battery parameters
        # -------------------------------------------------
        with open(processed / "battery_parameters.json", "r") as f:
            params = json.load(f)

        self.capacity_ah = params["capacity_ah"]
        self.soc_min = params["soc_min"]
        self.soc_max = params["soc_max"]
        self.nominal_voltage = params["nominal_voltage"]

        self.charge_efficiency = params["charge_efficiency"]
        self.discharge_efficiency = params["discharge_efficiency"]

        self.initial_soc = params["initial_soc"]

        # -------------------------------------------------
        # Load lookup tables
        # -------------------------------------------------
        self.ocv_table = pd.read_csv(processed / "battery_lookup.csv")
        self.resistance_table = pd.read_csv(
            processed / "resistance_lookup.csv"
        )

        # -------------------------------------------------
        # Battery state
        # -------------------------------------------------
        self.soc = self.initial_soc

        # Remaining capacity (Ah)
        self.remaining_capacity = self.capacity_ah * self.soc / 100.0

        self.current = 0.0
        self.ocv = self.get_ocv()
        self.internal_resistance = self.get_internal_resistance()

        # Stored energy (Wh)
        self.energy = self.remaining_capacity * self.ocv
        self.terminal_voltage = self.ocv

    # =====================================================
    # Lookup Functions
    # =====================================================

    def get_ocv(self):
        table = self.ocv_table.sort_values("soc")
        return float(np.interp(self.soc, table["soc"], table["ocv"]))

    def get_internal_resistance(self):
        table = self.resistance_table.sort_values("soc")
        resistance_mohm = np.interp(
            self.soc, table["soc"], table["resistance_mohm"]
        )
        return float(resistance_mohm / 1000.0)

    # =====================================================
    # Electrical Model
    # =====================================================

    def get_terminal_voltage(self, current, ocv, resistance):
        """Calculate terminal voltage using OCV and internal resistance.

        - Positive current: Discharging (Voltage drops below OCV)
        - Negative current: Charging (Voltage rises above OCV)
        """
        return ocv - (current * resistance)

    # =====================================================
    # Charge
    # =====================================================

    def charge(self, current, timestep_hours):
        """Charge the battery with positive current value (A)."""
        current = abs(current)
        added_ah = current * timestep_hours * self.charge_efficiency

        # Update remaining capacity & clamp
        min_capacity = self.capacity_ah * self.soc_min / 100.0
        max_capacity = self.capacity_ah * self.soc_max / 100.0

        self.remaining_capacity = max(
            min_capacity,
            min(self.remaining_capacity + added_ah, max_capacity),
        )

        # Derive SOC from capacity
        self.soc = (self.remaining_capacity / self.capacity_ah) * 100.0

        # Electrical updates (Charging current is negative in standard sign convention)
        self.current = -current
        self.ocv = self.get_ocv()
        self.internal_resistance = self.get_internal_resistance()
        self.terminal_voltage = self.get_terminal_voltage(
            self.current, self.ocv, self.internal_resistance
        )
        self.energy = self.remaining_capacity * self.ocv

    # =====================================================
    # Discharge
    # =====================================================

    def discharge(self, current, timestep_hours):
        """Discharge the battery with positive current value (A)."""
        current = abs(current)
        removed_ah = (current * timestep_hours) / self.discharge_efficiency

        # Update remaining capacity & clamp
        min_capacity = self.capacity_ah * self.soc_min / 100.0
        max_capacity = self.capacity_ah * self.soc_max / 100.0

        self.remaining_capacity = max(
            min_capacity,
            min(self.remaining_capacity - removed_ah, max_capacity),
        )

        # Derive SOC from capacity
        self.soc = (self.remaining_capacity / self.capacity_ah) * 100.0

        # Electrical updates
        self.current = current
        self.ocv = self.get_ocv()
        self.internal_resistance = self.get_internal_resistance()
        self.terminal_voltage = self.get_terminal_voltage(
            self.current, self.ocv, self.internal_resistance
        )
        self.energy = self.remaining_capacity * self.ocv
    # =====================================================
    # State Synchronization
    # =====================================================

    def set_state(
        self,
        soc,
        current=0.0,
        terminal_voltage=None,
    ):
        """Set the battery state in a controlled and consistent way.

        Parameters
        ----------
        soc : float
            Battery state of charge in percent.

        current : float, optional
            Battery current in amperes.
            Positive means discharging.
            Negative means charging.

        terminal_voltage : float, optional
            Measured terminal voltage.
            If not provided, terminal voltage is calculated
            from OCV, current, and internal resistance.

        Notes
        -----
        This method is intended for controlled state synchronization,
        such as updating a Digital Twin from measured battery data.
        """

        # -------------------------------------------------
        # Validate SOC
        # -------------------------------------------------
        if not self.soc_min <= soc <= self.soc_max:
            raise ValueError(
                f"SOC must be between {self.soc_min} and "
                f"{self.soc_max}. Received: {soc}"
            )

        # -------------------------------------------------
        # Update SOC and remaining capacity
        # -------------------------------------------------
        self.soc = float(soc)
        self.remaining_capacity = (
            self.capacity_ah * self.soc / 100.0
        )

        # -------------------------------------------------
        # Update electrical state from SOC
        # -------------------------------------------------
        self.current = float(current)
        self.ocv = self.get_ocv()
        self.internal_resistance = self.get_internal_resistance()

        if terminal_voltage is None:
            self.terminal_voltage = self.get_terminal_voltage(
                self.current,
                self.ocv,
                self.internal_resistance,
            )
        else:
            self.terminal_voltage = float(terminal_voltage)

        # -------------------------------------------------
        # Update stored energy
        # -------------------------------------------------
        self.energy = self.remaining_capacity * self.ocv
    # =====================================================
    # Getters
    # =====================================================

    def get_soc(self):
        return self.soc

    def get_voltage(self):
        return self.terminal_voltage

    def get_energy(self):
        return self.energy

    def get_power(self):
        """Calculate instantaneous electrical power at the battery terminals.

        Sign convention:
        - Positive power: Discharging
        - Negative power: Charging
        - Zero power: No current flow

        Returns
        -------
        float
            Terminal power in watts (W).
        """
        return self.terminal_voltage * self.current

    # =====================================================
    # Status
    # =====================================================

    def status(self):
        return {
            "SOC (%)": round(self.soc, 2),
            "Voltage (V)": round(self.terminal_voltage, 3),
            "OCV (V)": round(self.ocv, 3),
            "Current (A)": round(self.current, 3),
            "Resistance (Ohm)": round(self.internal_resistance, 5),
            "Energy (Wh)": round(self.energy, 3),
        }