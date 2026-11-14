import math
import numpy as np
from .battery import Battery


class ExtendedKalmanFilter:
    """
    2-state Extended Kalman Filter for BESS.

    State:
        x[0] = SOC (%)
        x[1] = V_RC (V)

    Measurement:
        terminal voltage (V)

    The EKF uses:
        - Battery OCV-SOC lookup table
        - Battery resistance-SOC lookup table
        - 1-RC Thevenin ECM
        - Current measurement
    """

    def __init__(
        self,
        battery: Battery,
        initial_soc=100.0,
        initial_v_rc=0.0,
        r1=0.03,
        c1=2000.0,
        q_soc=0.01,
        q_vrc=0.0001,
        r_voltage=0.01
    ):

        self.battery = battery

        # ---------------------------------------------------------
        # EKF parameters
        # ---------------------------------------------------------

        self.r1 = r1
        self.c1 = c1

        # Process-noise covariance
        self.q_soc = q_soc
        self.q_vrc = q_vrc

        # Measurement-noise covariance
        self.r_voltage = r_voltage

        # Battery parameters
        self.capacity_ah = battery.capacity_ah
        self.charge_efficiency = battery.charge_efficiency
        self.discharge_efficiency = battery.discharge_efficiency

        self.soc_min = battery.soc_min
        self.soc_max = battery.soc_max

        # ---------------------------------------------------------
        # State vector
        # ---------------------------------------------------------

        self.x = np.array(
            [
                float(initial_soc),
                float(initial_v_rc)
            ],
            dtype=float
        )

        # ---------------------------------------------------------
        # Covariance matrix
        # ---------------------------------------------------------

        self.P = np.array(
            [
                [1.0, 0.0],
                [0.0, 0.01]
            ],
            dtype=float
        )

        # Last values
        self.last_predicted_voltage = None
        self.last_innovation = None
        self.last_kalman_gain = np.zeros(2)
    # =============================================================
    # LOOKUP FUNCTIONS
    # =============================================================

    def _interpolate_ocv(self, soc):
        """
        Interpolate OCV from the battery OCV lookup table.
        """

        table = self.battery.ocv_table

        soc_values = table["soc"].to_numpy(dtype=float)
        ocv_values = table["ocv"].to_numpy(dtype=float)

        # np.interp requires ascending x values
        order = np.argsort(soc_values)

        soc_values = soc_values[order]
        ocv_values = ocv_values[order]

        soc = np.clip(
            soc,
            soc_values.min(),
            soc_values.max()
        )

        return float(
            np.interp(
                soc,
                soc_values,
                ocv_values
            )
        )

    def _interpolate_resistance(self, soc):
        """
        Interpolate internal resistance from SOC.

        Dataset stores resistance in milliohms.
        EKF uses ohms.
        """

        table = self.battery.resistance_table

        soc_values = table["soc"].to_numpy(dtype=float)
        resistance_values = table["resistance_mohm"].to_numpy(dtype=float)

        order = np.argsort(soc_values)

        soc_values = soc_values[order]
        resistance_values = resistance_values[order]

        soc = np.clip(
            soc,
            soc_values.min(),
            soc_values.max()
        )

        resistance_mohm = np.interp(
            soc,
            soc_values,
            resistance_values
        )

        return float(resistance_mohm / 1000.0)

    # =============================================================
    # BATTERY STATE EQUATION
    # =============================================================

    def _predict_soc(self, soc, current, timestep_hours):
        """
        Predict SOC using Coulomb counting.

        Convention:
            current > 0  -> discharge
            current < 0  -> charge
        """

        if current > 0:

            delta_soc = (
                current
                * timestep_hours
                / self.capacity_ah
                / self.discharge_efficiency
                * 100.0
            )

            predicted_soc = soc - delta_soc

        elif current < 0:

            charge_current = abs(current)

            delta_soc = (
                charge_current
                * timestep_hours
                / self.capacity_ah
                * self.charge_efficiency
                * 100.0
            )

            predicted_soc = soc + delta_soc

        else:

            predicted_soc = soc
        return float(
            np.clip(
                predicted_soc,
                self.soc_min,
                self.soc_max
            )
)

    # =============================================================
    # ECM PREDICTION
    # =============================================================

    def _predict_v_rc(self, v_rc, current, timestep_hours):
        """
        Predict RC polarization voltage.
        """

        dt = timestep_hours * 3600.0

        tau = self.r1 * self.c1

        alpha = math.exp(-dt / tau)

        return (
            alpha * v_rc
            + self.r1 * (1.0 - alpha) * current
        )

    def _predict_terminal_voltage(
        self,
        soc,
        v_rc,
        current
    ):
        """
        Terminal voltage:

        V = OCV(SOC) - I*R0(SOC) - V_RC
        """

        ocv = self._interpolate_ocv(soc)

        resistance = self._interpolate_resistance(soc)

        terminal_voltage = (
            ocv
            - current * resistance
            - v_rc
        )

        return float(terminal_voltage)

    # =============================================================
    # NUMERICAL DERIVATIVE
    # =============================================================

    def _calculate_dv_dsoc(
        self,
        soc,
        v_rc,
        current
    ):
        """
        Numerical derivative of terminal voltage
        with respect to SOC.
        """

        delta_soc = 0.01

        soc_low = np.clip(
            soc - delta_soc,
            self.soc_min,
            self.soc_max
        )

        soc_high = np.clip(
            soc + delta_soc,
            self.soc_min,
            self.soc_max
        )

        voltage_low = self._predict_terminal_voltage(
            soc_low,
            v_rc,
            current
        )

        voltage_high = self._predict_terminal_voltage(
            soc_high,
            v_rc,
            current
        )

        denominator = soc_high - soc_low

        if denominator == 0:
            return 0.0

        return (
            voltage_high - voltage_low
        ) / denominator

    # =============================================================
    # EKF PREDICTION STEP
    # =============================================================

    def predict(
        self,
        current,
        timestep_hours
    ):
        """
        EKF prediction step.
        """

        if timestep_hours < 0:
            raise ValueError(
                "timestep_hours cannot be negative."
            )

        soc = self.x[0]
        v_rc = self.x[1]

        # ---------------------------------------------
        # State prediction
        # ---------------------------------------------

        predicted_soc = self._predict_soc(
            soc,
            current,
            timestep_hours
        )

        predicted_v_rc = self._predict_v_rc(
            v_rc,
            current,
            timestep_hours
        )

        self.x = np.array(
            [
                predicted_soc,
                predicted_v_rc
            ],
            dtype=float
        )

        # ---------------------------------------------
        # State transition matrix
        # ---------------------------------------------

        dt = timestep_hours * 3600.0

        tau = self.r1 * self.c1

        alpha = math.exp(-dt / tau)

        F = np.array(
            [
                [1.0, 0.0],
                [0.0, alpha]
            ],
            dtype=float
        )

        # ---------------------------------------------
        # Process noise
        # ---------------------------------------------

        Q = np.array(
            [
                [self.q_soc, 0.0],
                [0.0, self.q_vrc]
            ],
            dtype=float
        )

        # ---------------------------------------------
        # Covariance prediction
        # ---------------------------------------------

        self.P = (
            F
            @ self.P
            @ F.T
            + Q
        )

        return self.x.copy()

    # =============================================================
    # EKF UPDATE STEP
    # =============================================================

    def update(
        self,
        measured_voltage,
        current
    ):
        """
        EKF measurement update using terminal voltage.
        """

        soc = self.x[0]
        v_rc = self.x[1]

        # ---------------------------------------------
        # Predicted voltage
        # ---------------------------------------------

        predicted_voltage = self._predict_terminal_voltage(
            soc,
            v_rc,
            current
        )

        self.last_predicted_voltage = predicted_voltage

        # ---------------------------------------------
        # Measurement innovation
        # ---------------------------------------------

        innovation = (
            measured_voltage
            - predicted_voltage
        )

        self.last_innovation = innovation

        # ---------------------------------------------
        # Measurement Jacobian
        # ---------------------------------------------

        dv_dsoc = self._calculate_dv_dsoc(
            soc,
            v_rc,
            current
        )

        H = np.array(
            [
                [dv_dsoc, -1.0]
            ],
            dtype=float
        )

        # ---------------------------------------------
        # Measurement noise
        # ---------------------------------------------

        R = np.array(
            [
                [self.r_voltage]
            ],
            dtype=float
        )

        # ---------------------------------------------
        # Innovation covariance
        # ---------------------------------------------

        S = (
            H
            @ self.P
            @ H.T
            + R
        )

        # ---------------------------------------------
        # Kalman gain
        # ---------------------------------------------

        K = (
            self.P
            @ H.T
            @ np.linalg.inv(S)
        )
        self.last_kalman_gain = K.copy()

        # ---------------------------------------------
        # State update
        # ---------------------------------------------

        self.x = (
            self.x
            + (
                K.flatten()
                * innovation
            )
        )

       # Keep SOC physically valid
        self.x[0] = np.clip(
            self.x[0],
            self.soc_min,
            self.soc_max
)
        # ---------------------------------------------
        # Covariance update
        # ---------------------------------------------

        I = np.eye(2)

        self.P = (
            (I - K @ H)
            @ self.P
        )

        return self.x.copy()

    # =============================================================
    # COMPLETE EKF STEP
    # =============================================================

    def step(
        self,
        current,
        measured_voltage,
        timestep_hours
    ):
        """
        Run prediction + measurement update.
        """

        self.predict(
            current=current,
            timestep_hours=timestep_hours
        )

        self.update(
            measured_voltage=measured_voltage,
            current=current
        )

        return self.get_state()

    # =============================================================
    # GETTERS
    # =============================================================

    def get_soc(self):
        return float(self.x[0])

    def get_v_rc(self):
        return float(self.x[1])

    def get_state(self):
        return {
            "soc": float(self.x[0]),
            "v_rc": float(self.x[1]),
            "predicted_voltage": self.last_predicted_voltage,
            "innovation": self.last_innovation
        }

    def get_covariance(self):
        return self.P.copy()

    def reset(
        self,
        initial_soc=100.0,
        initial_v_rc=0.0
    ):
        """
        Reset EKF state.
        """

        self.x = np.array(
            [
                float(initial_soc),
                float(initial_v_rc)
            ],
            dtype=float
        )

        self.P = np.array(
            [
                [1.0, 0.0],
                [0.0, 0.01]
            ],
            dtype=float
        )

        self.last_predicted_voltage = None
        self.last_innovation = None