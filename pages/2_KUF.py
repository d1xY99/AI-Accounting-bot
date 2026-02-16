import streamlit as st
import os

# ── Page config ──
st.set_page_config(page_title="KUF - BS BIRO", page_icon="📄", layout="centered")

# ── Provjera API ključa ──
if "api_key" not in st.session_state or not st.session_state.api_key:
    st.warning("API ključ nije unesen. Vrati se na početnu stranicu.")
    st.page_link("app.py", label="Idi na početnu stranicu", icon="🏠")
    st.stop()

# ── CSS ──
st.markdown("""
<style>
header {visibility:hidden;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
.stApp {background-color:#f6d9c0;}
.block-container {max-width:600px; padding-top:2rem;}

.logo-row {display:flex; align-items:center; gap:14px; margin-bottom:4px; justify-content:center;}
.logo-row img {height:52px; width:auto;}
.logo-row .app-title {font-size:2rem; font-weight:700; margin:0;}

.copyright {text-align:center; font-size:11px; color:#94a3b8; margin-top:30px;}
</style>
""", unsafe_allow_html=True)

# ── Logo ──
import os as _os
_logo_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "images", "logo.png")
if _os.path.exists(_logo_path):
    st.markdown(f"""
    <div class="logo-row">
        <img src="data:image/png;base64,{__import__('base64').b64encode(open(_logo_path,'rb').read()).decode()}" />
        <div class="app-title">KUF — BS BIRO</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="logo-row"><div class="app-title">KUF — BS BIRO</div></div>', unsafe_allow_html=True)

st.caption("Knjiga Ulaznih Faktura")

st.markdown("---")

st.info("KUF modul je trenutno u izradi. Ova funkcionalnost će biti dostupna uskoro.")

st.page_link("app.py", label="Nazad na početnu stranicu", icon="🏠", use_container_width=True)

st.markdown('<div class="copyright">Sva prava zadržana, Amir Basic</div>', unsafe_allow_html=True)
