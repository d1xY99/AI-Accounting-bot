import streamlit as st
import os

APP_PASSWORD = "112"

# ── Page config ──
st.set_page_config(page_title="BS BIRO", page_icon="📄", layout="centered")

# ── CSS ──
st.markdown("""
<style>
header {visibility:hidden;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
.stApp {background-color:#f6d9c0;}
.block-container {max-width:600px; padding-top:2rem;}

/* Logo + naslov */
.logo-row {display:flex; align-items:center; gap:14px; margin-bottom:4px; justify-content:center;}
.logo-row img {height:64px; width:auto;}
.logo-row .app-title {font-size:2.4rem; font-weight:700; margin:0;}

/* Dugmad */
button[kind="primary"] {
    background:#0e8a3e !important; color:white !important; border:none !important;
}
button[kind="primary"]:hover {
    background:#0b6e31 !important; color:white !important;
}

.copyright {text-align:center; font-size:11px; color:#94a3b8; margin-top:30px;}
</style>
""", unsafe_allow_html=True)

# ── Logo + naslov ──
import os as _os
_logo_path = _os.path.join(_os.path.dirname(__file__), "images", "logo.png")
if _os.path.exists(_logo_path):
    st.markdown(f"""
    <div class="logo-row">
        <img src="data:image/png;base64,{__import__('base64').b64encode(open(_logo_path,'rb').read()).decode()}" />
        <div class="app-title">BS BIRO</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="logo-row"><div class="app-title">BS BIRO</div></div>', unsafe_allow_html=True)

st.markdown('<p style="text-align:center; color:#64748b; margin-top:4px;">Automatska obrada PDF računa</p>', unsafe_allow_html=True)

# ── Provjera šifre ──
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("---")
    st.subheader("Prijava")

    password = st.text_input("Unesi šifru", type="password", placeholder="Šifra...")

    if st.button("Prijavi se", type="primary", use_container_width=True):
        if password == APP_PASSWORD:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Pogrešna šifra. Pokušaj ponovo.")

    st.markdown('<div class="copyright">Sva prava zadržana, Amir Basic</div>', unsafe_allow_html=True)
    st.stop()

# ── Prijavljeno — prikaži navigaciju ──
st.markdown("---")

st.subheader("Odaberi modul")

col1, col2 = st.columns(2)

with col1:
    st.page_link("pages/1_KIF.py", label="KIF — Knjiga Izlaznih Faktura", icon="📤", use_container_width=True)
    st.caption("Obrada izlaznih računa koje tvoja firma izdaje kupcima.")

with col2:
    st.page_link("pages/2_KUF.py", label="KUF — Knjiga Ulaznih Faktura", icon="📥", use_container_width=True)
    st.caption("Obrada ulaznih računa koje tvoja firma prima od dobavljača.")

st.markdown('<div class="copyright">Sva prava zadržana, Amir Basic</div>', unsafe_allow_html=True)
