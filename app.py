import streamlit as st
import pandas as pd
import os
import struct
from io import BytesIO
import xlwt
import tempfile
from pdf2image import convert_from_bytes
from PIL import Image
from processor import process_pdf, split_pdf_to_pages, count_pdf_pages, iter_pdf_pages, process_fiscal_pdf, process_kuf_pdf, KIF_HEADERS, KUF_HEADERS, DNEVNI_HEADERS
#
def get_app_password():
    try:
        pw = st.secrets.get("APP_PASSWORD", "")
        if pw:
            return pw
    except Exception:
        pass
    return os.environ.get("APP_PASSWORD", "")

APP_PASSWORD = get_app_password()

# ── Session state init ──
_params = st.query_params
if "authenticated" not in st.session_state:
    st.session_state.authenticated = _params.get("auth") == "1"
if "page" not in st.session_state:
    st.session_state.page = _params.get("page", "home")

# ── Page config (must be first Streamlit command) ──
_layout = "wide" if st.session_state.page in ("kif", "kuf", "dnevni") else "centered"
_logo_path = os.path.join(os.path.dirname(__file__), "images", "logo.png")
_icon = Image.open(_logo_path) if os.path.exists(_logo_path) else "📄"
st.set_page_config(page_title="BS BIRO BOT", page_icon=_icon, layout=_layout)

# ── Helpers ──
def get_logo_b64():
    logo_path = os.path.join(os.path.dirname(__file__), "images", "logo.png")
    if os.path.exists(logo_path):
        import base64
        return base64.b64encode(open(logo_path, "rb").read()).decode()
    return None

def get_api_key():
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY", "")

logo_b64 = get_logo_b64()


def _write_dbf(dataframe, headers, encoding="cp852"):
    """Kreira dBASE III DBF sa ručnim enkodiranjem za ispravan prikaz č, ć, š, ž, đ."""
    FIELD_LEN = 100
    lang_map = {"cp852": 0x64, "cp1250": 0xC8, "cp437": 0x01, "cp850": 0x02}
    lang_byte = lang_map.get(encoding, 0x00)
    n_fields = len(headers)
    n_records = len(dataframe)
    header_size = 32 + (n_fields * 32) + 1
    record_size = 1 + (n_fields * FIELD_LEN)

    buf = BytesIO()
    # ── Header (32 bytes) ──
    buf.write(struct.pack('<B', 0x03))              # Version: dBASE III
    buf.write(struct.pack('<3B', 26, 1, 1))         # Datum: YY MM DD
    buf.write(struct.pack('<I', n_records))          # Broj zapisa
    buf.write(struct.pack('<H', header_size))        # Veličina headera
    buf.write(struct.pack('<H', record_size))        # Veličina zapisa
    buf.write(b'\x00' * 17)                         # Reserved
    buf.write(struct.pack('<B', lang_byte))          # Language driver
    buf.write(b'\x00' * 2)                          # Reserved

    # ── Field descriptors (32 bytes each) ──
    for h in headers:
        name = h[:10].encode('ascii', errors='replace').ljust(11, b'\x00')
        buf.write(name)                             # Ime polja (11 bytes)
        buf.write(b'C')                             # Tip: Character
        buf.write(b'\x00' * 4)                      # Reserved
        buf.write(struct.pack('<B', FIELD_LEN))     # Dužina polja
        buf.write(b'\x00')                          # Decimal count
        buf.write(b'\x00' * 14)                     # Reserved
    buf.write(b'\r')                                # Header terminator

    # ── Records ──
    for _, row in dataframe.iterrows():
        buf.write(b' ')                             # Delete flag
        for h in headers:
            val = str(row.get(h, ""))
            encoded = val.encode(encoding, errors='replace')[:FIELD_LEN]
            buf.write(encoded.ljust(FIELD_LEN, b' '))
    buf.write(b'\x1a')                              # EOF marker
    return buf.getvalue()


# ═══════════════════════════════════════════
# HOME PAGE
# ═══════════════════════════════════════════
if st.session_state.page == "home":

    st.markdown("""
    <style>
    header {visibility:hidden;}
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    .stApp {background-color:#f6d9c0;}
    .block-container {max-width:600px; padding-top:2rem;}
    .logo-row {display:flex; align-items:center; gap:14px; margin-bottom:4px; justify-content:center;}
    .logo-row img {height:64px; width:auto;}
    .logo-row .app-title {font-size:2.4rem; font-weight:700; margin:0;}
    button[kind="primary"] {
        background:#0e8a3e !important; color:white !important; border:none !important;
    }
    button[kind="primary"]:hover {
        background:#0b6e31 !important; color:white !important;
    }
    .copyright {text-align:center; font-size:11px; color:#94a3b8; margin-top:30px;}
    </style>
    """, unsafe_allow_html=True)

    if logo_b64:
        st.markdown(f'<div class="logo-row"><img src="data:image/png;base64,{logo_b64}" /><div class="app-title">BS BIRO</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="logo-row"><div class="app-title">BS BIRO</div></div>', unsafe_allow_html=True)

    st.markdown('<p style="text-align:center; color:#64748b; margin-top:4px;">Automatska obrada faktura</p>', unsafe_allow_html=True)

    if not st.session_state.authenticated:
        st.markdown("---")
        st.subheader("Prijava")
        with st.form("login_form"):
            password = st.text_input("Unesi šifru", type="password", placeholder="Šifra...")
            submitted = st.form_submit_button("Prijavi se", type="primary", use_container_width=True)
            if submitted:
                if password == APP_PASSWORD:
                    st.session_state.authenticated = True
                    st.query_params["auth"] = "1"
                    st.rerun()
                else:
                    st.error("Pogrešna šifra. Pokušaj ponovo.")
        st.markdown('<div class="copyright">Sva prava zadržana, Amir Basic - basic.amir99@gmail.com</div>', unsafe_allow_html=True)
        st.stop()

    # Authenticated - show navigation
    st.markdown("---")
    st.subheader("Odaberi modul")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📤 KIF — Knjiga Izlaznih Faktura", use_container_width=True):
            st.session_state.page = "kif"
            st.query_params["page"] = "kif"
            st.rerun()
    with col2:
        if st.button("📥 KUF — Knjiga Ulaznih Faktura", use_container_width=True):
            st.session_state.page = "kuf"
            st.query_params["page"] = "kuf"
            st.rerun()
    with col3:
        if st.button("🧾 KIF — Dnevni prihod", use_container_width=True):
            st.session_state.page = "dnevni"
            st.query_params["page"] = "dnevni"
            st.rerun()

    st.markdown('<div class="copyright">Sva prava zadržana, Amir Basic - basic.amir99@gmail.com</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════
# KIF PAGE
# ═══════════════════════════════════════════
elif st.session_state.page == "kif":

    st.markdown("""
    <style>
    header {visibility:hidden;}
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    .block-container {max-width:100%; padding-top:1rem; padding-bottom:2rem; padding-left:2rem; padding-right:2rem;}
    .stApp {background-color:#f6d9c0;}
    [data-testid="stDataEditor"] {min-height:600px;}
    .logo-row {display:flex; align-items:center; gap:14px; margin-bottom:4px;}
    .logo-row img {height:52px; width:auto;}
    .logo-row .app-title {font-size:2rem; font-weight:700; margin:0;}
    .steps {background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:14px 18px; margin:10px 0 16px 0; font-size:13.5px; line-height:1.7; color:#334155;}
    .steps .copyright {margin-top:12px; padding-top:10px; border-top:1px solid #e2e8f0; font-size:11px; color:#94a3b8;}
    div.stDownloadButton > button {background:#0e8a3e; color:white; border:none; border-radius:8px; font-weight:500;}
    div.stDownloadButton > button:hover {background:#0b6e31; color:white;}
    #pdf_download > button {background:#18181b !important; color:white !important;}
    #pdf_download > button:hover {background:#3f3f46 !important; color:white !important;}
    button[kind="primary"] {background:#0e8a3e !important; color:white !important; border:none !important;}
    button[kind="primary"]:hover {background:#0b6e31 !important; color:white !important;}
    </style>
    """, unsafe_allow_html=True)

    # Header
    top_left, top_right = st.columns([3, 2])

    with top_left:
        if st.button("← Nazad", key="back_home"):
            st.session_state.page = "home"
            st.query_params["page"] = "home"
            st.rerun()

        if logo_b64:
            st.markdown(f'<div class="logo-row"><img src="data:image/png;base64,{logo_b64}" /><div class="app-title">KIF — BS BIRO</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="logo-row"><div class="app-title">KIF — BS BIRO</div></div>', unsafe_allow_html=True)

        st.caption("Knjiga Izlaznih Faktura")
        st.markdown("""
        <div class="steps">
            <strong>Kako koristiti:</strong><br>
            1. Upload-uj jedan ili više PDF računa (drag & drop ili klikni Browse)<br>
            2. Klikni <b>Obradi račune</b> — AI automatski izvlači podatke iz svakog PDF-a<br>
            3. Pregledaj i edituj podatke u tabeli ako treba<br>
            4. Preuzmi gotov Excel ili CSV fajl
            <div class="copyright">Sva prava zadržana, Amir Basic - basic.amir99@gmail.com</div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_files = st.file_uploader("Prevuci ili odaberi PDF račune", type=["pdf"], accept_multiple_files=True)

    with top_left:
        if not uploaded_files:
            st.info("Dodaj račune za početak obrade.")
            st.stop()

        st.write(f"**{len(uploaded_files)}** račun(a) odabrano")

        # Show only errors and warnings
        if st.session_state.get("logs"):
            for t, msg in st.session_state.logs:
                if t == "err":
                    st.error(msg, icon="❌")
                elif t == "warn":
                    st.warning(msg, icon="⚠️")

    # Session state
    if "results" not in st.session_state:
        st.session_state.results = []
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "pdf_map" not in st.session_state:
        st.session_state.pdf_map = {}

    with top_left:
        process_clicked = st.button("Obradi račune", type="primary", use_container_width=True)

    if process_clicked:
        api_key = get_api_key()
        with top_left:
            if not api_key:
                st.error("OpenAI API ključ nije pronađen. Dodaj ga u .streamlit/secrets.toml ili .env")
                st.stop()

        st.session_state.results = []
        st.session_state.logs = []
        st.session_state.pdf_map = {}
        st.session_state.labels = {}
        seen = set()

        # Prebrojaj ukupno stranica bez čuvanja svih bajtova u memoriji
        total = 0
        for file in uploaded_files:
            pdf_bytes = file.read()
            total += count_pdf_pages(pdf_bytes)
            file.seek(0)

        with top_left:
            with st.spinner("AI obrađuje račune, molimo sačekajte..."):
                progress = st.progress(0, text="Pokrećem obradu...")
                i = 0
                for file in uploaded_files:
                    pdf_bytes = file.read()
                    file_pages = count_pdf_pages(pdf_bytes)
                    for page_num, page_bytes in iter_pdf_pages(pdf_bytes):
                        label = f"{file.name} (str. {page_num})" if file_pages > 1 else file.name
                        progress.progress(i / total, text=f"Obrađujem {i+1}/{total}: {label}")
                        try:
                            data = process_pdf(page_bytes, filename=label, api_key=api_key)
                            broj = data.get("BRDOKFAKT", "")
                            if broj and broj in seen:
                                st.session_state.logs.append(("warn", f"{label} — duplikat računa {broj}"))
                            else:
                                seen.add(broj)
                                idx = len(st.session_state.results)
                                st.session_state.results.append(data)
                                st.session_state.pdf_map[idx] = page_bytes
                                st.session_state.labels[idx] = label
                                st.session_state.logs.append(("ok", f"{label} — {data.get('NAZIVPP','?')} — {data.get('IZNAKFT','?')} KM"))
                        except Exception as e:
                            st.session_state.logs.append(("err", f"{label} — {str(e)}"))
                        i += 1
                        progress.progress(i / total)
                    del pdf_bytes
                progress.progress(1.0, text=f"Gotovo! Obrađeno {len(st.session_state.results)} račun(a)")

    # Results
    if st.session_state.results:
        with top_left:
            st.divider()
            st.subheader("Podaci")
            st.caption("Klikni na polje u tabeli da edituješ prije downloada")

            df = pd.DataFrame(st.session_state.results, columns=KIF_HEADERS)
            for col in KIF_HEADERS:
                if col not in df.columns:
                    df[col] = ""

            edited_df = st.data_editor(df[KIF_HEADERS], use_container_width=True, hide_index=True, num_rows="dynamic", key="data_editor")

            def create_xls(dataframe):
                wb = xlwt.Workbook(encoding="utf-8")
                ws = wb.add_sheet("Racuni")
                for c, h in enumerate(KIF_HEADERS):
                    ws.write(0, c, h)
                for r, row in dataframe.iterrows():
                    for c, h in enumerate(KIF_HEADERS):
                        ws.write(r + 1, c, str(row.get(h, "")))
                output = BytesIO()
                wb.save(output)
                return output.getvalue()

            def create_dbf(dataframe):
                return _write_dbf(dataframe, KIF_HEADERS)

            st.divider()
            e1, e2, e3 = st.columns(3)
            with e1:
                st.download_button("Preuzmi DBF", create_dbf(edited_df), "racuni.dbf", type="primary", use_container_width=True)
            with e2:
                st.download_button("Preuzmi XLS", create_xls(edited_df), "racuni.xls", use_container_width=True)
            with e3:
                st.download_button("Preuzmi CSV", edited_df.to_csv(index=False, sep=";", encoding="utf-8-sig"), "racuni.csv", use_container_width=True)

        with top_right:
            st.subheader("PDF pregled")

            def preview_label(i):
                r = st.session_state.results[i]
                naziv = r.get("NAZIVPP", "?")
                broj = r.get("BRDOKFAKT", "")
                src = st.session_state.labels.get(i, "")
                parts = [naziv]
                if broj:
                    parts.append(f"#{broj}")
                if src:
                    parts.append(f"[{src}]")
                return " — ".join(parts)

            selected = st.selectbox(
                "Odaberi račun za pregled",
                options=range(len(st.session_state.results)),
                format_func=preview_label,
            )
            pdf_bytes = st.session_state.pdf_map.get(selected)
            if pdf_bytes:
                st.download_button("Preuzmi ovaj PDF", pdf_bytes, "racun.pdf", use_container_width=True, key="pdf_download")
                pages = convert_from_bytes(pdf_bytes, dpi=150)
                for page in pages:
                    st.image(page, use_container_width=True)

# ═══════════════════════════════════════════
# DNEVNI PRIHOD PAGE
# ═══════════════════════════════════════════
elif st.session_state.page == "dnevni":

    st.markdown("""
    <style>
    header {visibility:hidden;}
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    .block-container {max-width:100%; padding-top:1rem; padding-bottom:2rem; padding-left:2rem; padding-right:2rem;}
    .stApp {background-color:#f6d9c0;}
    [data-testid="stDataEditor"] {min-height:400px;}
    .logo-row {display:flex; align-items:center; gap:14px; margin-bottom:4px;}
    .logo-row img {height:52px; width:auto;}
    .logo-row .app-title {font-size:2rem; font-weight:700; margin:0;}
    .steps {background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:14px 18px; margin:10px 0 16px 0; font-size:13.5px; line-height:1.7; color:#334155;}
    .steps .copyright {margin-top:12px; padding-top:10px; border-top:1px solid #e2e8f0; font-size:11px; color:#94a3b8;}
    div.stDownloadButton > button {background:#0e8a3e; color:white; border:none; border-radius:8px; font-weight:500;}
    div.stDownloadButton > button:hover {background:#0b6e31; color:white;}
    #pdf_download_d > button {background:#18181b !important; color:white !important;}
    #pdf_download_d > button:hover {background:#3f3f46 !important; color:white !important;}
    button[kind="primary"] {background:#0e8a3e !important; color:white !important; border:none !important;}
    button[kind="primary"]:hover {background:#0b6e31 !important; color:white !important;}
    </style>
    """, unsafe_allow_html=True)

    top_left, top_right = st.columns([3, 2])

    with top_left:
        if st.button("← Nazad", key="back_home_d"):
            st.session_state.page = "home"
            st.query_params["page"] = "home"
            st.rerun()

        if logo_b64:
            st.markdown(f'<div class="logo-row"><img src="data:image/png;base64,{logo_b64}" /><div class="app-title">KIF Dnevni prihod — BS BIRO</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="logo-row"><div class="app-title">KIF Dnevni prihod — BS BIRO</div></div>', unsafe_allow_html=True)

        st.caption("Obrada fiskalnih računa — dnevni prihod")
        st.markdown("""
        <div class="steps">
            <strong>Kako koristiti:</strong><br>
            1. Skeniraj papir sa fiskalnim računima (do 5 računa na jednoj stranici)<br>
            2. Upload-uj PDF sken (drag & drop ili klikni Browse)<br>
            3. Klikni <b>Obradi fiskalne račune</b> — AI prepoznaje sve račune na stranici<br>
            4. Pregledaj i edituj podatke u tabeli<br>
            5. Preuzmi gotov XLS ili DBF fajl
            <div class="copyright">Sva prava zadržana, Amir Basic - basic.amir99@gmail.com</div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_files_d = st.file_uploader("Prevuci ili odaberi PDF sa fiskalnim računima", type=["pdf"], accept_multiple_files=True, key="fiscal_uploader")

    with top_left:
        if not uploaded_files_d:
            st.info("Dodaj skenirane fiskalne račune za početak obrade.")
            st.stop()

        st.write(f"**{len(uploaded_files_d)}** fajl(ova) odabrano")

        if st.session_state.get("d_logs"):
            for t, msg in st.session_state.d_logs:
                if t == "err":
                    st.error(msg, icon="❌")
                elif t == "warn":
                    st.warning(msg, icon="⚠️")

    if "d_results" not in st.session_state:
        st.session_state.d_results = []
    if "d_logs" not in st.session_state:
        st.session_state.d_logs = []
    if "d_pdf_map" not in st.session_state:
        st.session_state.d_pdf_map = {}

    with top_left:
        process_clicked_d = st.button("Obradi fiskalne račune", type="primary", use_container_width=True)

    if process_clicked_d:
        api_key = get_api_key()
        with top_left:
            if not api_key:
                st.error("OpenAI API ključ nije pronađen. Dodaj ga u .streamlit/secrets.toml ili .env")
                st.stop()

        st.session_state.d_results = []
        st.session_state.d_logs = []
        st.session_state.d_pdf_map = {}

        # Prebrojaj ukupno stranica bez čuvanja svih bajtova u memoriji
        total = 0
        for file in uploaded_files_d:
            pdf_bytes = file.read()
            total += count_pdf_pages(pdf_bytes)
            file.seek(0)

        with top_left:
            with st.spinner("AI obrađuje fiskalne račune, molimo sačekajte..."):
                progress = st.progress(0, text="Pokrećem obradu...")
                i = 0
                for file in uploaded_files_d:
                    pdf_bytes = file.read()
                    file_pages = count_pdf_pages(pdf_bytes)
                    for page_num, page_bytes in iter_pdf_pages(pdf_bytes):
                        label = f"{file.name} (str. {page_num})" if file_pages > 1 else file.name
                        progress.progress(i / total, text=f"Obrađujem {i+1}/{total}: {label}")
                        try:
                            fiscal_items = process_fiscal_pdf(page_bytes, filename=label, api_key=api_key)
                            for item in fiscal_items:
                                idx = len(st.session_state.d_results)
                                st.session_state.d_results.append(item)
                                st.session_state.d_pdf_map[idx] = page_bytes
                                st.session_state.d_logs.append(("ok", f"{label} — DI: {item.get('SADRZAJ','?')} — Datum: {item.get('DATUMDOK','?')}"))
                        except Exception as e:
                            st.session_state.d_logs.append(("err", f"{label} — {str(e)}"))
                        i += 1
                        progress.progress(i / total)
                    del pdf_bytes
                progress.progress(1.0, text=f"Gotovo! Pronađeno {len(st.session_state.d_results)} fiskalnih računa")

    if st.session_state.d_results:
        with top_left:
            st.divider()
            st.subheader("Podaci")
            st.caption("Klikni na polje u tabeli da edituješ prije downloada")

            df = pd.DataFrame(st.session_state.d_results, columns=DNEVNI_HEADERS)
            for col in DNEVNI_HEADERS:
                if col not in df.columns:
                    df[col] = ""

            edited_df = st.data_editor(df[DNEVNI_HEADERS], use_container_width=True, hide_index=True, num_rows="dynamic", key="data_editor_d")

            def create_xls_d(dataframe):
                wb = xlwt.Workbook(encoding="utf-8")
                ws = wb.add_sheet("DnevniPrihod")
                for c, h in enumerate(DNEVNI_HEADERS):
                    ws.write(0, c, h)
                for r, row in dataframe.iterrows():
                    for c, h in enumerate(DNEVNI_HEADERS):
                        ws.write(r + 1, c, str(row.get(h, "")))
                output = BytesIO()
                wb.save(output)
                return output.getvalue()

            def create_dbf_d(dataframe):
                return _write_dbf(dataframe, DNEVNI_HEADERS)

            st.divider()
            e1, e2, e3 = st.columns(3)
            with e1:
                st.download_button("Preuzmi DBF", create_dbf_d(edited_df), "dnevni_prihod.dbf", type="primary", use_container_width=True)
            with e2:
                st.download_button("Preuzmi XLS", create_xls_d(edited_df), "dnevni_prihod.xls", use_container_width=True)
            with e3:
                st.download_button("Preuzmi CSV", edited_df.to_csv(index=False, sep=";", encoding="utf-8-sig"), "dnevni_prihod.csv", use_container_width=True)

        with top_right:
            st.subheader("PDF pregled")

            def preview_label_d(i):
                r = st.session_state.d_results[i]
                datum = r.get("DATUMDOK", "?")
                sadrzaj = r.get("SADRZAJ", "?")
                return f"DI: {sadrzaj} — {datum}"

            selected = st.selectbox(
                "Odaberi račun za pregled",
                options=range(len(st.session_state.d_results)),
                format_func=preview_label_d,
                key="fiscal_preview_select",
            )
            pdf_bytes = st.session_state.d_pdf_map.get(selected)
            if pdf_bytes:
                st.download_button("Preuzmi ovaj PDF", pdf_bytes, "fiskalni.pdf", use_container_width=True, key="pdf_download_d")
                pages = convert_from_bytes(pdf_bytes, dpi=150)
                for page in pages:
                    st.image(page, use_container_width=True)

# ═══════════════════════════════════════════
# KUF PAGE
# ═══════════════════════════════════════════
elif st.session_state.page == "kuf":

    st.markdown("""
    <style>
    header {visibility:hidden;}
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    .block-container {max-width:100%; padding-top:1rem; padding-bottom:2rem; padding-left:2rem; padding-right:2rem;}
    .stApp {background-color:#f6d9c0;}
    [data-testid="stDataEditor"] {min-height:600px;}
    .logo-row {display:flex; align-items:center; gap:14px; margin-bottom:4px;}
    .logo-row img {height:52px; width:auto;}
    .logo-row .app-title {font-size:2rem; font-weight:700; margin:0;}
    .steps {background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:14px 18px; margin:10px 0 16px 0; font-size:13.5px; line-height:1.7; color:#334155;}
    .steps .copyright {margin-top:12px; padding-top:10px; border-top:1px solid #e2e8f0; font-size:11px; color:#94a3b8;}
    div.stDownloadButton > button {background:#0e8a3e; color:white; border:none; border-radius:8px; font-weight:500;}
    div.stDownloadButton > button:hover {background:#0b6e31; color:white;}
    #pdf_download_k > button {background:#18181b !important; color:white !important;}
    #pdf_download_k > button:hover {background:#3f3f46 !important; color:white !important;}
    button[kind="primary"] {background:#0e8a3e !important; color:white !important; border:none !important;}
    button[kind="primary"]:hover {background:#0b6e31 !important; color:white !important;}
    </style>
    """, unsafe_allow_html=True)

    # Header
    top_left, top_right = st.columns([3, 2])

    with top_left:
        if st.button("← Nazad", key="back_home_k"):
            st.session_state.page = "home"
            st.query_params["page"] = "home"
            st.rerun()

        if logo_b64:
            st.markdown(f'<div class="logo-row"><img src="data:image/png;base64,{logo_b64}" /><div class="app-title">KUF — BS BIRO</div></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="logo-row"><div class="app-title">KUF — BS BIRO</div></div>', unsafe_allow_html=True)

        st.caption("Knjiga Ulaznih Faktura")
        st.markdown("""
        <div class="steps">
            <strong>Kako koristiti:</strong><br>
            1. Upload-uj jedan ili više PDF ulaznih računa (drag & drop ili klikni Browse)<br>
            2. Klikni <b>Obradi račune</b> — AI automatski izvlači podatke iz svakog PDF-a<br>
            3. Pregledaj i edituj podatke u tabeli ako treba<br>
            4. Preuzmi gotov Excel ili CSV fajl
            <div class="copyright">Sva prava zadržana, Amir Basic - basic.amir99@gmail.com</div>
        </div>
        """, unsafe_allow_html=True)

        uploaded_files_k = st.file_uploader("Prevuci ili odaberi PDF ulazne račune", type=["pdf"], accept_multiple_files=True, key="kuf_uploader")

    with top_left:
        if not uploaded_files_k:
            st.info("Dodaj ulazne račune za početak obrade.")
            st.stop()

        st.write(f"**{len(uploaded_files_k)}** račun(a) odabrano")

        if st.session_state.get("k_logs"):
            for t, msg in st.session_state.k_logs:
                if t == "err":
                    st.error(msg, icon="❌")
                elif t == "warn":
                    st.warning(msg, icon="⚠️")

    # Session state
    if "k_results" not in st.session_state:
        st.session_state.k_results = []
    if "k_logs" not in st.session_state:
        st.session_state.k_logs = []
    if "k_pdf_map" not in st.session_state:
        st.session_state.k_pdf_map = {}
    if "k_labels" not in st.session_state:
        st.session_state.k_labels = {}

    with top_left:
        process_clicked_k = st.button("Obradi račune", type="primary", use_container_width=True, key="process_kuf")

    if process_clicked_k:
        api_key = get_api_key()
        with top_left:
            if not api_key:
                st.error("OpenAI API ključ nije pronađen. Dodaj ga u .streamlit/secrets.toml ili .env")
                st.stop()

        st.session_state.k_results = []
        st.session_state.k_logs = []
        st.session_state.k_pdf_map = {}
        st.session_state.k_labels = {}
        seen = set()

        # Prebrojaj ukupno stranica bez čuvanja svih bajtova u memoriji
        total = 0
        for file in uploaded_files_k:
            pdf_bytes = file.read()
            total += count_pdf_pages(pdf_bytes)
            file.seek(0)

        with top_left:
            with st.spinner("AI obrađuje ulazne račune, molimo sačekajte..."):
                progress = st.progress(0, text="Pokrećem obradu...")
                i = 0
                for file in uploaded_files_k:
                    pdf_bytes = file.read()
                    file_pages = count_pdf_pages(pdf_bytes)
                    for page_num, page_bytes in iter_pdf_pages(pdf_bytes):
                        label = f"{file.name} (str. {page_num})" if file_pages > 1 else file.name
                        progress.progress(i / total, text=f"Obrađujem {i+1}/{total}: {label}")
                        try:
                            data = process_kuf_pdf(page_bytes, filename=label, api_key=api_key)
                            broj = data.get("BROJFAKT", "")
                            if broj and broj in seen:
                                st.session_state.k_logs.append(("warn", f"{label} — duplikat računa {broj}"))
                            else:
                                seen.add(broj)
                                idx = len(st.session_state.k_results)
                                st.session_state.k_results.append(data)
                                st.session_state.k_pdf_map[idx] = page_bytes
                                st.session_state.k_labels[idx] = label
                                st.session_state.k_logs.append(("ok", f"{label} — {data.get('NAZIVPP','?')} — {data.get('IZNSAPDV','?')} KM"))
                        except Exception as e:
                            st.session_state.k_logs.append(("err", f"{label} — {str(e)}"))
                        i += 1
                        progress.progress(i / total)
                    del pdf_bytes
                progress.progress(1.0, text=f"Gotovo! Obrađeno {len(st.session_state.k_results)} račun(a)")

    # Results
    if st.session_state.k_results:
        with top_left:
            st.divider()
            st.subheader("Podaci")
            st.caption("Klikni na polje u tabeli da edituješ prije downloada")

            df = pd.DataFrame(st.session_state.k_results, columns=KUF_HEADERS)
            for col in KUF_HEADERS:
                if col not in df.columns:
                    df[col] = ""

            edited_df = st.data_editor(df[KUF_HEADERS], use_container_width=True, hide_index=True, num_rows="dynamic", key="data_editor_k")

            def create_xls_k(dataframe):
                wb = xlwt.Workbook(encoding="utf-8")
                ws = wb.add_sheet("UlazniRacuni")
                for c, h in enumerate(KUF_HEADERS):
                    ws.write(0, c, h)
                for r, row in dataframe.iterrows():
                    for c, h in enumerate(KUF_HEADERS):
                        ws.write(r + 1, c, str(row.get(h, "")))
                output = BytesIO()
                wb.save(output)
                return output.getvalue()

            def create_dbf_k(dataframe):
                return _write_dbf(dataframe, KUF_HEADERS)

            st.divider()
            e1, e2, e3 = st.columns(3)
            with e1:
                st.download_button("Preuzmi DBF", create_dbf_k(edited_df), "kuf.dbf", type="primary", use_container_width=True)
            with e2:
                st.download_button("Preuzmi XLS", create_xls_k(edited_df), "kuf.xls", use_container_width=True)
            with e3:
                st.download_button("Preuzmi CSV", edited_df.to_csv(index=False, sep=";", encoding="utf-8-sig"), "kuf.csv", use_container_width=True)

        with top_right:
            st.subheader("PDF pregled")

            def preview_label_k(i):
                r = st.session_state.k_results[i]
                naziv = r.get("NAZIVPP", "?")
                broj = r.get("BROJFAKT", "")
                src = st.session_state.k_labels.get(i, "")
                parts = [naziv]
                if broj:
                    parts.append(f"#{broj}")
                if src:
                    parts.append(f"[{src}]")
                return " — ".join(parts)

            selected = st.selectbox(
                "Odaberi račun za pregled",
                options=range(len(st.session_state.k_results)),
                format_func=preview_label_k,
                key="kuf_preview_select",
            )
            pdf_bytes = st.session_state.k_pdf_map.get(selected)
            if pdf_bytes:
                st.download_button("Preuzmi ovaj PDF", pdf_bytes, "ulazni_racun.pdf", use_container_width=True, key="pdf_download_k")
                pages = convert_from_bytes(pdf_bytes, dpi=150)
                for page in pages:
                    st.image(page, use_container_width=True)
