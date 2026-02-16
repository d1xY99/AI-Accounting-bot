import streamlit as st
import pandas as pd
import os
import tempfile
from io import BytesIO
from openpyxl import Workbook
from pdf2image import convert_from_bytes
from processor import process_pdf, KIF_HEADERS

# ── Page config ──
st.set_page_config(page_title="BS BIRO", page_icon="📄", layout="wide")

# ── CSS ──
st.markdown("""
<style>
header {visibility:hidden;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
.block-container {max-width:100%; padding-top:1rem; padding-bottom:2rem; padding-left:2rem; padding-right:2rem;}
[data-testid="stDataEditor"] {min-height:600px;}
</style>
""", unsafe_allow_html=True)

# ── Header + Upload (ista širina kao tabela) ──
top_left, top_right = st.columns([3, 2])

with top_left:
    st.title("BS BIRO")
    st.caption("Automatska obrada PDF računa")

    uploaded_files = st.file_uploader(
        "Prevuci ili odaberi PDF račune",
        type=["pdf"],
        accept_multiple_files=True,
    )

if not uploaded_files:
    st.info("Dodaj račune za početak obrade.")
    st.stop()

with top_left:
    st.write(f"**{len(uploaded_files)}** račun(a) odabrano")

# ── Session state ──
if "results" not in st.session_state:
    st.session_state.results = []
if "logs" not in st.session_state:
    st.session_state.logs = []
if "pdf_map" not in st.session_state:
    st.session_state.pdf_map = {}

# ── API key (tiho iz secrets ili env) ──
def get_api_key():
    try:
        key = st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("OPENAI_API_KEY", "")

# ── Obrada ──
with top_left:
    process_clicked = st.button("Obradi račune", type="primary", use_container_width=True)

if process_clicked:

    api_key = get_api_key()
    if not api_key:
        st.error("OpenAI API ključ nije pronađen. Dodaj ga u .streamlit/secrets.toml ili .env")
        st.stop()

    st.session_state.results = []
    st.session_state.logs = []
    st.session_state.pdf_map = {}

    progress = st.progress(0, text="Pokrećem obradu...")
    seen = set()

    for i, file in enumerate(uploaded_files):
        progress.progress(i / len(uploaded_files), text=f"Obrađujem {i+1}/{len(uploaded_files)}: {file.name}")
        try:
            pdf_bytes = file.read()
            data = process_pdf(pdf_bytes, filename=file.name, api_key=api_key)

            broj = data.get("BRDOKFAKT", "")
            if broj and broj in seen:
                st.session_state.logs.append(("warn", f"{file.name} — duplikat računa {broj}"))
                continue

            seen.add(broj)
            idx = len(st.session_state.results)
            st.session_state.results.append(data)
            st.session_state.pdf_map[idx] = pdf_bytes
            st.session_state.logs.append(("ok", f"{file.name} — {data.get('NAZIVPP','?')} — {data.get('IZNAKFT','?')} KM"))

        except Exception as e:
            st.session_state.logs.append(("err", f"{file.name} — {str(e)}"))

        progress.progress((i + 1) / len(uploaded_files))

    progress.progress(1.0, text=f"Gotovo! Obrađeno {len(st.session_state.results)} račun(a)")

# ── Rezultati ──
if st.session_state.results:

    # ── Lijeva kolona (status + tabela + export) / Desna kolona (PDF) ──
    col_table, col_pdf = st.columns([3, 2])

    with col_table:
        # Status log
        st.divider()
        for t, msg in st.session_state.logs:
            if t == "ok":
                st.success(msg, icon="✅")
            elif t == "err":
                st.error(msg, icon="❌")
            else:
                st.warning(msg, icon="⚠️")

        st.divider()
        st.subheader("Podaci")
        st.caption("Klikni na polje u tabeli da edituješ prije downloada")

        df = pd.DataFrame(st.session_state.results, columns=KIF_HEADERS)
        for col in KIF_HEADERS:
            if col not in df.columns:
                df[col] = ""

        edited_df = st.data_editor(
            df[KIF_HEADERS],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key="data_editor",
        )

        # Export
        def create_excel(dataframe):
            output = BytesIO()
            wb = Workbook()
            ws = wb.active
            ws.title = "Racuni"
            for c, h in enumerate(KIF_HEADERS, 1):
                ws.cell(row=1, column=c, value=h)
            for r, row in dataframe.iterrows():
                for c, h in enumerate(KIF_HEADERS, 1):
                    ws.cell(row=r + 2, column=c, value=row.get(h, ""))
            wb.save(output)
            return output.getvalue()

        st.divider()
        e1, e2 = st.columns(2)
        with e1:
            st.download_button(
                "Preuzmi Excel",
                create_excel(edited_df),
                "racuni.xlsx",
                type="primary",
                use_container_width=True,
            )
        with e2:
            st.download_button(
                "Preuzmi CSV",
                edited_df.to_csv(index=False, sep=";", encoding="utf-8-sig"),
                "racuni.csv",
                use_container_width=True,
            )

    with col_pdf:
        st.divider()
        st.subheader("PDF pregled")

        selected = st.selectbox(
            "Odaberi račun za pregled",
            options=range(len(st.session_state.results)),
            format_func=lambda i: f"{st.session_state.results[i].get('NAZIVPP','?')} — {st.session_state.results[i].get('BRDOKFAKT','')}",
        )

        pdf_bytes = st.session_state.pdf_map.get(selected)
        if pdf_bytes:
            st.download_button("Preuzmi ovaj PDF", pdf_bytes, "racun.pdf", use_container_width=True)
            pages = convert_from_bytes(pdf_bytes, dpi=150)
            for page in pages:
                st.image(page, use_container_width=True)
