import math


# =====================================================================
# INDUCED DRAFT FAN MOTOR PROTECTION ENGINE (50/50/51)
#    GE IFC66KD2A electromechanical relay (single-phase, per-phase A & C),
#    per GEK-49949 / P101-17-1823.10-0002 Rev. 0.
#
#    51 (Long Time Inverse time-overcurrent):
#       GE never published a closed-form equation for the IFC66/IAC66
#       "Long Time Inverse" curve — only printed time-current graphs. The
#       standard reproduction used across GE's own digital relay manuals
#       (F650, 750/760, MIFII-N / GEK-106618C) is the 5-constant IAC
#       polynomial:
#           T = TDM x [A + B/(M-C) + D/(M-C)^2 + E/(M-C)^3]
#       where M = multiple of the 51 tap (relay secondary current / tap).
#       "IAC Inverse Long" constants (GEK-106618C Sec 2.4.1.4):
#           A=0.3754, B=17.8307, C=0.32, D=-23.7187, E=23.8978
#       This is NOT an IEEE C37.112 curve (no Long Time curve exists in
#       that standard) and is NOT the IEC Long-Time curve either — do not
#       substitute either of those.
#
#    50A (instantaneous, tap H 30-150A): trips immediately, no time delay.
#    50B (high-dropout instantaneous, tap L 2-4A / H 4-8A): an overload
#       ALARM element — picks up above its pickup setting and (per
#       GEK-49949) drops out only once current falls below ~80% of that
#       pickup. Pickup is estimated here as dropout / 0.8 (documented
#       dropout ratio); full hysteresis/latching is not modeled — this
#       reports the static pickup/dropout thresholds and where the given
#       current sits relative to them.
# =====================================================================
class MotorTimeOvercurrentRelay:
    IAC_LONG = {"A": 0.3754, "B": 17.8307, "C": 0.32, "D": -23.7187, "E": 23.8978}

    def __init__(self, ct_ratio, ct_secondary_rating, tap_51, time_dial,
                 pickup_50a, dropout_50b, target_seal_in=0.2,
                 motor_fla=None, locked_rotor_amps=None):
        self.ct_ratio = ct_ratio
        self.ct_secondary_rating = ct_secondary_rating
        self.effective_ratio = (ct_ratio / ct_secondary_rating) if ct_secondary_rating > 0 else ct_ratio
        self.tap_51 = tap_51
        self.time_dial = time_dial
        self.pickup_50a = pickup_50a          # relay secondary amps
        self.dropout_50b = dropout_50b        # relay secondary amps
        self.pickup_50b = dropout_50b / 0.8   # estimated pickup (dropout is >=80% of pickup per GEK-49949)
        self.target_seal_in = target_seal_in
        self.motor_fla = motor_fla                     # primary amps, optional, for display/pu
        self.locked_rotor_amps = locked_rotor_amps      # primary amps, optional, for display/pu

    def relay_current(self, i_primary):
        """Convert a primary current (A) to relay secondary current (A)."""
        return i_primary / self.effective_ratio if self.effective_ratio > 0 else 0.0

    def calculate_51_trip_time(self, i_relay_sec):
        """Returns trip time in seconds, or None if below pickup (M <= 1)."""
        if self.tap_51 <= 0:
            return None
        m = i_relay_sec / self.tap_51
        if m <= 1.0:
            return None
        c = self.IAC_LONG["C"]
        x = m - c
        if x <= 0:
            return None
        bracket = (self.IAC_LONG["A"]
                   + self.IAC_LONG["B"] / x
                   + self.IAC_LONG["D"] / (x ** 2)
                   + self.IAC_LONG["E"] / (x ** 3))
        t = self.time_dial * bracket
        return max(t, 0.0)

    def evaluate_protection(self, i_primary):
        i_sec = self.relay_current(i_primary)
        m_51 = (i_sec / self.tap_51) if self.tap_51 > 0 else 0.0
        t51 = self.calculate_51_trip_time(i_sec)
        trip_51 = t51 is not None
        trip_50a = i_sec >= self.pickup_50a
        alarm_50b = i_sec >= self.pickup_50b

        is_trip = trip_51 or trip_50a
        if trip_50a:
            status = "INSTANTANEOUS TRIP (50A)"
        elif trip_51:
            status = f"TIME-DELAYED TRIP (51) — {t51:.2f}s"
        elif alarm_50b:
            status = "OVERLOAD ALARM (50B)"
        else:
            status = "SAFE"

        return {
            "i_relay_sec": i_sec,
            "multiple_of_pickup_51": m_51,
            "t51": t51,
            "trip_51": trip_51,
            "trip_50a": trip_50a,
            "alarm_50b": alarm_50b,
            "is_trip": is_trip,
            "status": status,
        }


# =====================================================================
# BACKUP INSTANTANEOUS OVERCURRENT RELAY (50)
#    GE HFC22B2A, per GEK-49826C / P101-17-1823.10-0002 Sec 5.1.2.
#    Two single-phase instantaneous units in one case, on a separate,
#    higher-ratio CT so it won't saturate under high fault current the
#    way the 50/50/51's lower-ratio CT might.
# =====================================================================
class BackupInstantaneousRelay:
    def __init__(self, ct_ratio, ct_secondary_rating, pickup_amps):
        self.ct_ratio = ct_ratio
        self.ct_secondary_rating = ct_secondary_rating
        self.effective_ratio = (ct_ratio / ct_secondary_rating) if ct_secondary_rating > 0 else ct_ratio
        self.pickup_amps = pickup_amps  # relay secondary amps

    def relay_current(self, i_primary):
        return i_primary / self.effective_ratio if self.effective_ratio > 0 else 0.0

    def evaluate_protection(self, i_primary):
        i_sec = self.relay_current(i_primary)
        is_trip = i_sec >= self.pickup_amps
        return {
            "i_relay_sec": i_sec,
            "is_trip": is_trip,
            "status": "INSTANTANEOUS TRIP (50)" if is_trip else "SAFE",
        }
