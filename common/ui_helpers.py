import streamlit as st


def render_placeholder(title, caption, note="🚧 Coming soon — this relay type is being added next."):
    st.title(title)
    st.caption(caption)
    st.info(note)


def slider_with_exact_input(container, label, min_v, max_v, default, step, key, help_text=None):
    slider_key = f"{key}__slider"
    number_key = f"{key}__number"

    if key not in st.session_state:
        st.session_state[key] = default

    if slider_key not in st.session_state:
        st.session_state[slider_key] = default

    if number_key not in st.session_state:
        st.session_state[number_key] = default

    def _on_slider_change():
        v = st.session_state[slider_key]
        st.session_state[key] = v
        st.session_state[number_key] = v

    def _on_number_change():
        v = st.session_state[number_key]
        v = min(max(v, min_v), max_v)
        st.session_state[key] = v
        st.session_state[slider_key] = v

    col_s, col_n = container.columns([2.4, 1])
    with col_s:
        st.slider(
            label, min_value=min_v, max_value=max_v, step=step,
            key=slider_key, on_change=_on_slider_change, help=help_text
        )
    with col_n:
        st.number_input(
            "Exact", min_value=min_v, max_value=max_v, step=step,
            key=number_key, on_change=_on_number_change, label_visibility="collapsed"
        )

    return st.session_state[key]
