import streamlit as st

st.title("⚡ POMI Protection Relay Suite")
st.caption("Protection settings calculation, commissioning-injection assistance, and settings verification for POMI's generator, transformer, and motor protection relays.")

st.markdown(
    """
This app helps engineers work through the protection relay settings for POMI's
generator, transformer, and motor equipment. For each relay it provides:

- **Live simulation** — enter operating currents and see the real-time trip/restraint verdict against the relay's characteristic curve.
- **Commissioning & injection tool** — calculates the exact secondary current to inject at a test set for a target test point.
- **Test point verification** — log actual measured test results and compare them against the calculated characteristic.
- **PDF / CSV export** — for keeping a record of settings and test results.

Pick an equipment category from the sidebar to get started.
"""
)

st.markdown("### 🧭 Available Equipment")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### ⚡ Generator")
    st.write(
        "Generator Differential Protection (87G) — GE G60 numerical dual-breakpoint "
        "characteristic, or GE CFD22B4A legacy product-restraint characteristic."
    )

with col2:
    st.markdown("#### 🔌 Transformer")
    st.write(
        "Transformer differential protection covering:\n"
        "- Excitation Transformer (EXCT)\n"
        "- Generator Step-Up Transformer (GSUT)\n"
        "- Overall GSUT-GEN (backup, 3-winding)\n"
        "- Auxiliary Transformer *(awaiting data)*"
    )

with col3:
    st.markdown("#### 🌀 Motor")
    st.write(
        "Motor overcurrent protection covering:\n"
        "- Induced Draft (ID) Fan — 50/50/51 time-overcurrent"
    )
