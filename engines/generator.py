import cmath
import math


# =====================================================================
# CORE GENERATOR DIFFERENTIAL RELAY ENGINE (87G)
#    Modes:
#      GENERATOR         - GE G60-style dual-breakpoint numerical characteristic:
#                           flat at Pickup until Break1, Slope1 from Break1 to Break2,
#                           Slope2 beyond Break2. Settings/ranges per G60 instruction manual.
#      GENERATOR_LEGACY   - GE CFD22A/B (e.g. CFD22B4A), per GEK-34124E: a PRODUCT-RESTRAINT
#                           relay. Restraint is based on the SMALLER of the two terminal
#                           currents (not their average/sum), balancing at a fixed 10%
#                           differential up to ~rated current. No breakpoints, no field-
#                           adjustable 2nd slope, no unrestrained high-set element.
# =====================================================================
class AdvancedDifferentialRelay:
    def __init__(self, mode, mva_rated, kv_rated,
                 ct_ratio_N=1.0, ct_ratio_T=1.0, ct_secondary_rating=5.0,
                 i_pickup=0.10, slope_1=15.0, slope_2=60.0,
                 break_1=1.10, break_2=6.00,
                 i_unrestrained=None,
                 convention="IEEE", ct_polarity="OPPOSITE",
                 target_amps=None):
        self.mode = mode.upper()  # 'GENERATOR' (GE G60) or 'GENERATOR_LEGACY' (GE CFD22B4A)
        self.mva_rated = mva_rated
        self.kv_rated = kv_rated
        self.ct_ratio_N = ct_ratio_N  # Neutral side CT primary rating
        self.ct_ratio_T = ct_ratio_T  # Terminal side CT primary rating
        self.ct_secondary_rating = ct_secondary_rating
        self.effective_ratio_N = (ct_ratio_N / ct_secondary_rating) if ct_secondary_rating > 0 else ct_ratio_N
        self.effective_ratio_T = (ct_ratio_T / ct_secondary_rating) if ct_secondary_rating > 0 else ct_ratio_T
        self.i_pickup = i_pickup
        self.s1 = slope_1 / 100.0
        self.s2 = slope_2 / 100.0
        self.break_1 = break_1
        self.break_2 = break_2
        self.i_unrestrained = i_unrestrained if i_unrestrained is not None else 1e6
        self.convention = convention.upper()
        self.ct_polarity = ct_polarity
        self.target_amps = target_amps

        self.i_rated_pri = (mva_rated * 1000.0) / (math.sqrt(3) * self.kv_rated) if self.kv_rated > 0 else 1.0

        self.i_rated_sec_N = self.i_rated_pri / self.effective_ratio_N if self.effective_ratio_N > 0 else 1.0
        self.i_rated_sec_T = self.i_rated_pri / self.effective_ratio_T if self.effective_ratio_T > 0 else 1.0

        if self.mode == "GENERATOR_LEGACY" and target_amps is not None and self.i_rated_sec_N > 0:
            self.i_pickup = target_amps / self.i_rated_sec_N
            self.s2 = self.s1
            self.i_unrestrained = 1e6

    def calculate_trip_threshold(self, i_rest_pu):
        if self.mode == "GENERATOR_LEGACY":
            return self.i_pickup + (self.s1 * i_rest_pu)

        if i_rest_pu <= self.break_1:
            return self.i_pickup
        elif i_rest_pu <= self.break_2:
            return self.i_pickup + self.s1 * (i_rest_pu - self.break_1)
        else:
            return self.i_pickup + self.s1 * (self.break_2 - self.break_1) + self.s2 * (i_rest_pu - self.break_2)

    def evaluate_protection(self, i_primary_N, angle_N_deg, i_primary_T, angle_T_deg):
        i_N_sec_mag = i_primary_N / self.effective_ratio_N if self.effective_ratio_N > 0 else 0.0
        i_T_sec_mag = i_primary_T / self.effective_ratio_T if self.effective_ratio_T > 0 else 0.0

        i_N_pu_mag = i_N_sec_mag / self.i_rated_sec_N if self.i_rated_sec_N > 0 else 0.0
        i_T_pu_mag = i_T_sec_mag / self.i_rated_sec_T if self.i_rated_sec_T > 0 else 0.0

        rad_N = math.radians(angle_N_deg)
        rad_T = math.radians(angle_T_deg)

        vec_N_pu = cmath.rect(i_N_pu_mag, rad_N)
        vec_T_pu = cmath.rect(i_T_pu_mag, rad_T)

        if self.ct_polarity == "SAME":
            vec_op = vec_T_pu + vec_N_pu
        else:
            vec_op = vec_T_pu - vec_N_pu

        i_op_pu = abs(vec_op)

        if self.mode == "GENERATOR_LEGACY":
            i_rest_pu = min(abs(vec_T_pu), abs(vec_N_pu))
        elif self.convention == "IEEE":
            i_rest_pu = (abs(vec_T_pu) + abs(vec_N_pu)) / 2.0
        else:
            i_rest_pu = abs(vec_T_pu) + abs(vec_N_pu)

        i_threshold_pu = self.calculate_trip_threshold(i_rest_pu)

        is_unrestrained_trip = i_op_pu >= self.i_unrestrained
        is_restrained_trip = i_op_pu > i_threshold_pu
        is_trip = is_unrestrained_trip or is_restrained_trip

        status_text = "SAFE"
        if is_unrestrained_trip:
            status_text = "UNRESTRAINED TRIP"
        elif is_restrained_trip:
            status_text = "SLOPE TRIP"

        return {
            "i_op_pu": i_op_pu,
            "i_rest_pu": i_rest_pu,
            "i_threshold_pu": i_threshold_pu,
            "is_trip": is_trip,
            "is_unrestrained": is_unrestrained_trip,
            "status": status_text,
            "i_N_pu_mag": i_N_pu_mag,
            "i_T_pu_mag": i_T_pu_mag
        }
