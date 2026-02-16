import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from processor import process_pdf, KIF_HEADERS

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="BS BIRO - Obrada Računa",
    page_icon="📄",
    layout="wide",
)

# ---------------------------------------------------
# SHADCN-LIKE STYLE
# ---------------------------------------------------
st.markdown("""
<style>

.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

html, body, [class*="css"]  {
    font-family: Inter, ui-sans-serif, system-ui;
}

/* HEADER */
.app-title {
    font-size: 1.9rem;
    font-weight: 600;
    letter-spacing: -0.02em;
}

.app-subtitle {
    color: #71717a;
    font-size: 0.95rem;
    margin-top: 0.25rem;
}

/* CARDS */
.card {
    border: 1px solid #e4e4e7;
    background: white;
    border-radius: 14px;
    padding: 1.25rem 1.25rem;
    margin-bottom: 1rem;
}

.card-muted {
    background: #fafafa;
}

/* BUTTONS */
.stButton>button {
    border-radius: 10px;
    font-weight: 500;
    border: 1px solid #e4e4e7;
}

.stButton>button[kind="primary"] {
    background: black;
    color: white;
    border: none;
}

/* BADGES */
.badge {
    display: block;
    padding: 8px 12px;
    border-radius: 10px;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 6px;
}

.badge-success { background:#ecfdf5; color:#047857; }
.badge-error   { background:#fef2f2; color:#b91c1c; }
.badge-warn    { background:#fffbeb; color:#b45309; }

/* DATA EDITOR */
.stDataEditor {
    border: 1px solid #e4e4e7;
    border-radius: 12px;
    overflow: hidden;
}

/* FILE UPLOAD */
[data-testid="stFileUploader"] {
    border: 2px dashed #e4e4e7;
    border-radius: 14px;
    padding: 20px;
    background: #fafafa;
}

</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# HEADER
# ---------------------------------------------------
st.markdown("""
<div class="card card-muted">
    <div class="app-title">BS BIRO</div>
    <div class="app-subtitle">
        AI ekstrakcija podataka iz PDF računa → Excel spreman za knjigovodstvo
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# SIDEBAR SETTINGS
# ---------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Postavke")
    api_key = st.text_input("OpenAI API ključ", type="password")
    st.caption("Ključ se koristi samo u ovoj sesiji.")

if not api_key:
    st.warning("Unesi OpenAI API ključ da bi aplikacija radila.")
    st.stop()

# ---------------------------------------------------
# FILE UPLOAD
# ---------------------------------------------------
st.markdown('<div class="card">', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Prevuci PDF račune ovdje",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.caption("Podržano: više računa odjednom • AI automatski prepoznaje dobavljača, iznos i broj računa")
    st.stop()

st.success(f"{len(uploaded_files)} fajlova spremno za obradu")
st.markdown('</div>', unsafe_allow_html=True)

# ---------------------------------------------------
# SESSION STATE
# ---------------------------------------------------
if "results" not in st.session_state:
    st.session_state.results = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()

# ---------------------------------------------------
# PROCESS BUTTON
# ---------------------------------------------------
if st.button("▶ Obradi račune", type="primary", use_container_width=True):

    st.session_state.results = []
    st.session_state.processed_files = set()

    progress = st.progress(0, text="Pokrećem obradu...")
    log_container = st.container()

    seen_numbers = set()

    for i, file in enumerate(uploaded_files):

        progress.progress(
            i / len(uploaded_files),
            text=f"Obrađujem {file.name}"
        )

        with log_container:
            with st.spinner(f"AI obrađuje {file.name}..."):
                try:
                    pdf_bytes = file.read()
                    data = process_pdf(pdf_bytes, filename=file.name, api_key=api_key)

                    broj = data.get("BRDOKFAKT", "")
                    if broj and broj in seen_numbers:
                        st.markdown(f'<div class="badge badge-warn">{file.name} • duplikat {broj}</div>', unsafe_allow_html=True)
                        continue

                    seen_numbers.add(broj)
                    st.session_state.results.append(data)

                    st.markdown(
                        f'<div class="badge badge-success">{file.name} • {data.get("NAZIVPP","?")} • {data.get("IZNAKFT","?")} KM</div>',
                        unsafe_allow_html=True
                    )

                except Exception as e:
                    st.markdown(
                        f'<div class="badge badge-error">{file.name} • Greška: {str(e)}</div>',
                        unsafe_allow_html=True
                    )

    progress.progress(1.0, text="Obrada završena")

# ---------------------------------------------------
# RESULTS TABLE
# ---------------------------------------------------
if st.session_state.results:

    st.markdown("""
    <div class="card">
    <h3>Rezultati</h3>
    <p style="color:#71717a;margin-top:-6px">
    Klikni u polje i ispravi ako AI pogriješi prije exporta
    </p>
    """, unsafe_allow_html=True)

    df = pd.DataFrame(st.session_state.results, columns=KIF_HEADERS)

    for col in KIF_HEADERS:
        if col not in df.columns:
            df[col] = ""

    edited_df = st.data_editor(
        df[KIF_HEADERS],
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True,
    )

    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------
    # EXPORTS
    # ---------------------------------------------------
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

    excel_data = create_excel(edited_df)
    csv_data = edited_df.to_csv(index=False, sep=";", encoding="utf-8-sig")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="⬇ Excel",
            data=excel_data,
            file_name="racuni.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            label="⬇ CSV",
            data=csv_data,
            file_name="racuni.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
