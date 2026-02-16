import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from processor import process_pdf, KIF_HEADERS

st.set_page_config(
    page_title="BS BIRO - Obrada Računa",
    page_icon="📄",
    layout="wide",
)

# CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #888;
        font-size: 1rem;
        margin-bottom: 2rem;
    }
    .status-ok { color: #00c853; }
    .status-err { color: #ff5252; }
    .status-wait { color: #ffa726; }
    .stDataEditor { font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📄 BS BIRO - Obrada Računa</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Upload PDF račune, AI izvuče podatke, ti preuzmeš Excel</div>', unsafe_allow_html=True)

# API key
api_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
if not api_key:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Unesi svoj OpenAI API ključ")

if not api_key:
    st.warning("Unesi OpenAI API ključ u sidebar-u ili postavi ga u Streamlit secrets.")
    st.stop()

# Upload
uploaded_files = st.file_uploader(
    "Prevuci PDF fajlove ovdje ili klikni Browse",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Upload-uj jedan ili više PDF računa za obradu.")
    st.stop()

st.write(f"**{len(uploaded_files)}** PDF fajl(ova) odabrano")

# Session state za rezultate
if "results" not in st.session_state:
    st.session_state.results = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()

# Obradi dugme
if st.button("▶ Obradi račune", type="primary", use_container_width=True):
    st.session_state.results = []
    st.session_state.processed_files = set()

    progress = st.progress(0, text="Pokrećem obradu...")
    status_container = st.container()

    seen_numbers = set()

    for i, file in enumerate(uploaded_files):
        progress.progress(
            (i) / len(uploaded_files),
            text=f"Obrađujem {i+1}/{len(uploaded_files)}: {file.name}",
        )

        with status_container:
            with st.spinner(f"⏳ AI obrađuje {file.name}..."):
                try:
                    pdf_bytes = file.read()
                    data = process_pdf(pdf_bytes, filename=file.name, api_key=api_key)

                    # Duplikat provjera
                    broj = data.get("BRDOKFAKT", "")
                    if broj and broj in seen_numbers:
                        st.warning(f"⚠️ {file.name} - duplikat računa {broj}, preskočen")
                        continue

                    seen_numbers.add(broj)
                    st.session_state.results.append(data)
                    st.session_state.processed_files.add(file.name)
                    st.success(f"✅ {file.name} - {data.get('NAZIVPP', '?')} - {data.get('IZNAKFT', '?')} KM")

                except Exception as e:
                    st.error(f"❌ {file.name} - Greška: {str(e)}")

    progress.progress(1.0, text=f"Gotovo! Obrađeno {len(st.session_state.results)} račun(a)")

# Prikaži rezultate
if st.session_state.results:
    st.divider()
    st.subheader("Rezultati")
    st.caption("Možeš editovati polja direktno u tabeli prije downloada")

    df = pd.DataFrame(st.session_state.results, columns=KIF_HEADERS)
    # Osiguraj da sve kolone postoje
    for col in KIF_HEADERS:
        if col not in df.columns:
            df[col] = ""

    edited_df = st.data_editor(
        df[KIF_HEADERS],
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "REDBR": st.column_config.NumberColumn("R.BR", width="small"),
            "TIPDOK": st.column_config.TextColumn("TIP", width="small"),
            "BRDOKFAKT": st.column_config.TextColumn("BR.DOKUMENTA", width="medium"),
            "DATUMF": st.column_config.TextColumn("DATUM", width="medium"),
            "NAZIVPP": st.column_config.TextColumn("NAZIV PP", width="large"),
            "SJEDISTEPP": st.column_config.TextColumn("SJEDIŠTE PP", width="large"),
            "IDDVPP": st.column_config.TextColumn("ID BROJ", width="medium"),
            "JIBPUPP": st.column_config.TextColumn("PDV BROJ", width="medium"),
            "IZNAKFT": st.column_config.TextColumn("UKUPNO", width="medium"),
            "IZNOSNOV": st.column_config.TextColumn("NETO", width="medium"),
            "IZNPDV": st.column_config.TextColumn("PDV", width="medium"),
        },
    )

    # Excel download
    st.divider()

    def create_excel(dataframe):
        output = BytesIO()
        wb = Workbook()
        ws = wb.active
        ws.title = "Racuni"

        for col, header in enumerate(KIF_HEADERS, start=1):
            ws.cell(row=1, column=col, value=header)

        for row_idx, row in dataframe.iterrows():
            for col_idx, header in enumerate(KIF_HEADERS, start=1):
                ws.cell(row=row_idx + 2, column=col_idx, value=row.get(header, ""))

        wb.save(output)
        return output.getvalue()

    col1, col2 = st.columns(2)
    with col1:
        excel_data = create_excel(edited_df)
        st.download_button(
            label="📥 Download Excel",
            data=excel_data,
            file_name="racuni.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
    with col2:
        csv_data = edited_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
        st.download_button(
            label="📥 Download CSV",
            data=csv_data,
            file_name="racuni.csv",
            mime="text/csv",
            use_container_width=True,
        )
