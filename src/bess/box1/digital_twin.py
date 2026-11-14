import math
from .battery import Battery


class DigitalTwin:
    """
    Digital Twin of a Battery Energy Storage System.

    Features
    --------
    - Direct state synchronization using measurements
    - Model-based SOC prediction
    - SOC synchronization-error monitoring
    - 1-RC Thevenin ECM voltage prediction
    """

    def __init__(self, battery: Battery):

        self.battery = battery

        # Synchronization error information
        self.last_error = 0.0
        self.error_history = []

        # Fitted 1-RC Thevenin ECM parameters
        self.r1 = 0.03
        self.c1 = 2000.0

        # RC polarization voltage
        self.v_rc = 0.0

    # =====================================================
    # ECM VOLTAGE PREDICTION
    # =====================================================

    def predict_ecm_voltage(
        self,
        current,
        timestep_hours
    ):
        """
        Predict the next terminal voltage using a
        1-RC Thevenin ECM.

        Positive current = discharge.
        Negative current = charge.

        The battery SOC is also advanced by one timestep.
        """

        if timestep_hours < 0:
            raise ValueError(
                "timestep_hours cannot be negative."
            )

        # -------------------------------------------------
        # 1. Advance battery SOC
        # -------------------------------------------------

        if current > 0:

            self.battery.discharge(
                current=current,
                timestep_hours=timestep_hours
            )

        elif current < 0:

            self.battery.charge(
                current=abs(current),
                timestep_hours=timestep_hours
            )

        else:

            self.battery.set_state(
                soc=self.battery.get_soc(),
                current=0.0
            )

        # -------------------------------------------------
        # 2. Convert timestep to seconds
        # -------------------------------------------------

        dt = timestep_hours * 3600.0

        # -------------------------------------------------
        # 3. Get SOC-dependent battery parameters
        # -------------------------------------------------

        ocv = self.battery.get_ocv()
        r0 = self.battery.get_internal_resistance()

        # -------------------------------------------------
        # 4. RC time constant
        # -------------------------------------------------

        tau = self.r1 * self.c1

        # -------------------------------------------------
        # 5. Exponential coefficient
        # -------------------------------------------------

        alpha = math.exp(-dt / tau)

        # -------------------------------------------------
        # 6. Update RC polarization voltage
        # -------------------------------------------------

        self.v_rc = (
            alpha * self.v_rc
            + self.r1 * (1.0 - alpha) * current
        )

        # -------------------------------------------------
        # 7. Calculate ECM terminal voltage
        # -------------------------------------------------

        terminal_voltage = (
            ocv
            - current * r0
            - self.v_rc
        )

        # -------------------------------------------------
        # 8. Store predicted terminal voltage
        # -------------------------------------------------

        self.battery.terminal_voltage = terminal_voltage

        return terminal_voltage

    # =====================================================
    # STATE SYNCHRONIZATION
    # =====================================================

    def update(
        self,
        measured_soc,
        measured_current=0.0,
        measured_terminal_voltage=None
    ):
        """
        Synchronize the Digital Twin with measured data.
        """

        self.battery.set_state(
            soc=measured_soc,
            current=measured_current,
            terminal_voltage=measured_terminal_voltage
        )

    # =====================================================
    # MODEL-BASED STATE PREDICTION
    # =====================================================

    def predict(
        self,
        current,
        timestep_hours
    ):
        """
        Predict the next Digital Twin state.

        Positive current = discharge.
        Negative current = charge.
        """

        if timestep_hours < 0:
            raise ValueError(
                "timestep_hours cannot be negative."
            )

        if current > 0:

            self.battery.discharge(
                current=current,
                timestep_hours=timestep_hours
            )

        elif current < 0:

            self.battery.charge(
                current=abs(current),
                timestep_hours=timestep_hours
            )

        else:

            self.battery.set_state(
                soc=self.battery.get_soc(),
                current=0.0
            )

        return self.battery.status()

    # =====================================================
    # SYNCHRONIZATION ERROR
    # =====================================================

    def calculate_error(
        self,
        physical_battery: Battery
    ) -> float:

        physical_soc = physical_battery.get_soc()
        twin_soc = self.battery.get_soc()

        soc_error = abs(
            physical_soc - twin_soc
        )

        self.last_error = soc_error
        self.error_history.append(soc_error)

        return soc_error

    def calculate_voltage_error(
        self,
        physical_battery: Battery
    ) -> float:

        physical_voltage = physical_battery.get_voltage()
        twin_voltage = self.battery.get_voltage()

        return abs(
            physical_voltage - twin_voltage
        )

    def calculate_energy_error(
        self,
        physical_battery: Battery
    ) -> float:

        physical_energy = physical_battery.get_energy()
        twin_energy = self.battery.get_energy()

        return abs(
            physical_energy - twin_energy
        )

    def is_synchronized(
        self,
        threshold=1.0
    ) -> bool:

        return self.last_error <= threshold

    # =====================================================
    # GETTERS
    # =====================================================

    def get_current_soc(self) -> float:
        return self.battery.get_soc()

    def get_rc_voltage(self):
        return self.v_rc

    def get_current_voltage(self) -> float:
        return self.battery.get_voltage()

    def get_current_energy(self) -> float:
        return self.battery.get_energy()

    def get_error_history(self):
        return self.error_history.copy()

    # =====================================================
    # RESET
    # =====================================================

    def reset_ecm(self):
        self.v_rc = 0.0

    def reset(self) -> None:

        self.error_history.clear()
        self.last_error = 0.0
        self.v_rc = 0.0