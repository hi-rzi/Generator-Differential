import cmath
import math


# =====================================================================
# TRANSFORMER DIFFERENTIAL RELAY ENGINE (87T)
#    GE CAC1-10-M3 (2-winding: EXCT, GSUT) / CAC2-10-M3 (3-winding: Overall
#    GSUT-GEN backup) family, per P101-17-1823.16-0001 Rev. 5.
#
#    Each winding carries its own CT-matching tap T_i, selected (per the
#    source document) so that the tap-corrected current at rated load is
#    close to the relay's own rated tap current (I_N, typically 5A):
#        i_tap_pu_i = (i_secondary_i * T_i) / ct_secondary_rating_i
#    This intentionally reproduces the small residual "mismatch" between
#    windings at rated load rather than assuming a perfect 0 pu balance.
#
#    Operate current is the magnitude of the phasor sum of all windings'
#    tap-corrected currents (winding 0 is the reference/HV winding; the
#    OPPOSITE/SAME polarity convention flips the others, exactly mirroring
#    the 2-winding Generator engine's N/T convention, generalized to N
#    windings).
#
#    Trip threshold = max(Minimum Operate %, Bias % x restraint) - confirmed
#    directly by the source document's plain-language description of the
#    relay's "bias setting (slope)" and "minimum operating current setting".
#    HOC is an unrestrained instantaneous element: trips if operate current
#    >= HOC x tap current (i.e. >= HOC pu, since 1.0 pu = I_N).
#
#    Restraint convention (average vs. sum across windings) is NOT fully
#    pinned down by the scanned Setting Summary pages for the 3-winding
#    case, so — consistent with the existing IEEE/IEC toggle on the
#    Generator engine — it is exposed as a selectable convention rather
#    than silently assumed.
# =====================================================================
class TransformerDifferentialRelay:
    def __init__(self, mva_rated, windings, bias_pct, min_operate_pct, hoc_multiple,
                 convention="IEEE", ct_polarity="OPPOSITE"):
        """
        windings: list of dicts, each with keys:
            name, kv, ct_ratio, ct_secondary_rating, tap
          windings[0] is the reference (HV) winding.
        """
        self.mva_rated = mva_rated
        self.windings = [dict(w) for w in windings]
        self.bias = bias_pct / 100.0
        self.min_operate_pu = min_operate_pct / 100.0
        self.hoc_pu = hoc_multiple
        self.convention = convention.upper()
        self.ct_polarity = ct_polarity.upper()

        for w in self.windings:
            w["effective_ratio"] = (w["ct_ratio"] / w["ct_secondary_rating"]) if w["ct_secondary_rating"] > 0 else w["ct_ratio"]
            w["i_rated_pri"] = (mva_rated * 1000.0) / (math.sqrt(3) * w["kv"]) if w["kv"] > 0 else 1.0
            w["i_rated_sec"] = w["i_rated_pri"] / w["effective_ratio"] if w["effective_ratio"] > 0 else w["i_rated_pri"]

    def calculate_trip_threshold(self, i_rest_pu):
        return max(self.min_operate_pu, self.bias * i_rest_pu)

    def evaluate_protection(self, winding_inputs):
        """winding_inputs: list of (i_primary_amps, angle_deg), same order as self.windings."""
        vecs_pu = []
        mags_pu = []
        for idx, (w, (i_pri, angle_deg)) in enumerate(zip(self.windings, winding_inputs)):
            i_sec = i_pri / w["effective_ratio"] if w["effective_ratio"] > 0 else 0.0
            i_tap_pu = (i_sec * w["tap"]) / w["ct_secondary_rating"] if w["ct_secondary_rating"] > 0 else 0.0
            vec = cmath.rect(i_tap_pu, math.radians(angle_deg))
            if idx > 0 and self.ct_polarity == "OPPOSITE":
                vec = -vec
            vecs_pu.append(vec)
            mags_pu.append(abs(vec))

        vec_op = sum(vecs_pu)
        i_op_pu = abs(vec_op)

        if self.convention == "IEEE":
            i_rest_pu = sum(mags_pu) / len(mags_pu)
        else:
            i_rest_pu = sum(mags_pu)

        i_threshold_pu = self.calculate_trip_threshold(i_rest_pu)

        is_unrestrained_trip = i_op_pu >= self.hoc_pu
        is_restrained_trip = i_op_pu > i_threshold_pu
        is_trip = is_unrestrained_trip or is_restrained_trip

        status_text = "SAFE"
        if is_unrestrained_trip:
            status_text = "UNRESTRAINED TRIP (HOC)"
        elif is_restrained_trip:
            status_text = "SLOPE TRIP"

        return {
            "i_op_pu": i_op_pu,
            "i_rest_pu": i_rest_pu,
            "i_threshold_pu": i_threshold_pu,
            "is_trip": is_trip,
            "is_unrestrained": is_unrestrained_trip,
            "status": status_text,
            "winding_mags_pu": mags_pu,
        }
