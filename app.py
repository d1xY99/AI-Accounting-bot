import streamlit as st
import openai
import os

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

# ── Auto-load ključa iz secrets ili env ──
def try_load_key():
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY", "")

if "api_key" not in st.session_state:
    auto_key = try_load_key()
    if auto_key:
        st.session_state.api_key = auto_key

# ── API ključ ──
has_key = "api_key" in st.session_state and st.session_state.api_key

if not has_key:
    st.markdown("---")
    st.subheader("Unesi OpenAI API ključ")
    st.caption("Ključ se čuva samo u trenutnoj sesiji i ne šalje se nikome.")

    key_input = st.text_input("API ključ", type="password", placeholder="sk-proj-...")

    if st.button("Sačuvaj ključ", type="primary", use_container_width=True):
        if not key_input.strip():
            st.error("Ključ ne može biti prazan.")
        else:
            with st.spinner("Provjeravam ključ..."):
                try:
                    client = openai.OpenAI(api_key=key_input.strip())
                    client.models.list()
                    st.session_state.api_key = key_input.strip()
                    st.success("Ključ je validan!")
                    st.rerun()
                except openai.AuthenticationError:
                    st.error("Neispravan API ključ. Provjeri i pokušaj ponovo.")
                except Exception as e:
                    st.error(f"Greška pri provjeri: {str(e)}")

    st.markdown('<div class="copyright">Sva prava zadržana, Amir Basic</div>', unsafe_allow_html=True)
    st.stop()

# ── Ključ postoji — prikaži navigaciju ──
st.markdown("---")
st.markdown('<p style="text-align:center; color:#0e8a3e; font-weight:600; font-size:14px;">API ključ aktivan</p>', unsafe_allow_html=True)

st.subheader("Odaberi modul")

col1, col2 = st.columns(2)

with col1:
    st.page_link("pages/1_KIF.py", label="KIF — Knjiga Izlaznih Faktura", icon="📤", use_container_width=True)
    st.caption("Obrada izlaznih računa koje tvoja firma izdaje kupcima.")

with col2:
    st.page_link("pages/2_KUF.py", label="KUF — Knjiga Ulaznih Faktura", icon="📥", use_container_width=True)
    st.caption("Obrada ulaznih računa koje tvoja firma prima od dobavljača.")

st.markdown("---")

# Opcija za promjenu ključa
with st.expander("Promijeni API ključ"):
    new_key = st.text_input("Novi API ključ", type="password", placeholder="sk-proj-...", key="new_key_input")
    if st.button("Ažuriraj ključ"):
        if new_key.strip():
            with st.spinner("Provjeravam..."):
                try:
                    client = openai.OpenAI(api_key=new_key.strip())
                    client.models.list()
                    st.session_state.api_key = new_key.strip()
                    st.success("Ključ ažuriran!")
                    st.rerun()
                except openai.AuthenticationError:
                    st.error("Neispravan API ključ.")
                except Exception as e:
                    st.error(f"Greška: {str(e)}")

st.markdown('<div class="copyright">Sva prava zadržana, Amir Basic</div>', unsafe_allow_html=True)
