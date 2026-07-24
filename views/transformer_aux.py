import os

import streamlit as st

from common.sld import ASSET_DIR
from common.ui_helpers import render_placeholder

render_placeholder(
    "🔌 Auxiliary Transformer Differential Protection",
    "Unit Auxiliary Transformer differential protection.",
    note="🚧 Awaiting relay settings data — this page will be built out once the "
         "Auxiliary Transformer protection data is available."
)

_aux_sld_path = os.path.join(ASSET_DIR, "transformer_aux.png")
if os.path.isfile(_aux_sld_path):
    st.subheader("🗺️ Protection Zone — Single Line Diagram")
    st.caption("Shows where the CTs sit and what falls inside the 87AT differential zone.")
    st.image(_aux_sld_path, use_container_width=True)
