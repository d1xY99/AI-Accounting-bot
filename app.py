import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from processor import process_pdf, KIF_HEADERS

# ------------------------------------------------
# PAGE
# ------------------------------------------------
st.set_page_config(
    page_title="BS BIRO",
    page_icon="📄",
    layout="wide",
)

# ------------------------------------------------
# MODERN APP STYLE
# ------------------------------------------------
st.markdown("""
<style>

/* page width */
.block-container {
    max-width: 1300px;
    padding-top: 1.5rem;
    padding-bottom: 4rem;
}

/* typography */
html, body, [class*="css"] {
    font-family: Inter, system-ui, sans-serif;
}

/* header */
.header {
    display:flex;
    align-items:center;
    justify-content:space-between;
    margin-bottom:1.5rem;
}

.title {
    font-size:1.7rem;
    font-weight:600;
    letter-spacing:-0.02em;
}

.subtitle {
    color:#6b7280;
    font-size:0.95rem;
}

/* dropzone */
[data-testid="stFileUploader"] {
    border:2px dashed #e5e7eb;
    border-radius:16px;
    padding:45px;
    background:#fafafa;
    transition:all .2s ease;
}

[data-testid="stFileUploader"]:hover {
    border-color:#9ca3af;
    background:#f3f4f6;
}

/* table */
.stDataEditor {
    border:1px solid #e5e7eb;
    border-radius:14px;
    overflow:hidden;
}

/* process log */
.log-success {
    background:#f0fdf4;
    border:1px solid #bbf7d0;
    padding:8px 12px;
    border-radius:10px;
    margin-bottom:6px;
    font-size:13px;
}

.log-error {
    background:#fef2f2;
    border:1px solid #fecaca;
    padding:8px 12px;
    border-radius:10px;
    margin-bottom:6px;
    font-size:13px;
}

.log-warn {
    background:#fffbeb;
    border:1px solid #fde68a;
    padding:8px 12px;
    border-radius:10px;
    margin-bottom:6px;
    font-size:13px;
}

/* sticky export bar */
.export-bar {
    position:fixed;
    bottom:0;
    left:0;
    right:0;
    background:white;
    border-top:1px solid #e5e7eb;
    padding:14px 30px;
    box-shadow:0 -6px 20px rgba(0,0,0,0.04);
}

</style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# HEADER
# ------------------------------------------------
st.markdown("""
<div class="header">
    <div>
        <div class="title">BS BIRO</div>
        <div class="subtitle">Automatsko prepoznavanje podataka iz PDF računa</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------
# UPLOAD
# ------------------------------------------------
uploaded_files = st.file_uploader(
    "Prevuci ili odaberi PDF račune",
    type=["pdf"],
    accept_multiple_files=True,
)

if not uploaded_files:
    st.info("Dodaj račune da započne obrada")
    st.stop()

st.success(f"{len(uploaded_files)} računa spremno")

# ------------------------------------------------
# STATE
# ------------------------------------------------
if "results" not in st.session_state:
    st.session_state.results = []
if "logs" not in st.session_state:
    st.session_state.logs = []

# ------------------------------------------------
# PROCESS BUTTON
# ------------------------------------------------
if st.button("Obradi račune", use_container_width=True):

    st.session_state.results = []
    st.session_state.logs = []

    progress = st.progress(0)

    seen = set()

    for i, file in enumerate(uploaded_files):

        try:
            data = process_pdf(file.read(), filename=file.name)

            broj = data.get("BRDOKFAKT", "")

            if broj and broj in seen:
                st.session_state.logs.append(("warn", f"{file.name} duplikat {broj}"))
                continue

            seen.add(broj)
            st.session_state.results.append(data)
            st.session_state.logs.append(("ok", f"{file.name} • {data.get('NAZIVPP','?')} • {data.get('IZNAKFT','?')} KM"))

        except Exception as e:
            st.session_state.logs.append(("err", f"{file.name} • {str(e)}"))

        progress.progress((i+1)/len(uploaded_files))

# ------------------------------------------------
# RESULTS VIEW
# ------------------------------------------------
if st.session_state.results:

    left, right = st.columns([1,2])

    # LOG PANEL
    with left:
        st.subheader("Obrada")
        for t, msg in st.session_state.logs:
            cls = {"ok":"log-success","err":"log-error","warn":"log-warn"}[t]
            st.markdown(f'<div class="{cls}">{msg}</div>', unsafe_allow_html=True)

    # TABLE PANEL
    with right:
        st.subheader("Pregled i ispravka")

        df = pd.DataFrame(st.session_state.results, columns=KIF_HEADERS)
        for col in KIF_HEADERS:
            if col not in df.columns:
                df[col] = ""

        edited_df = st.data_editor(
            df[KIF_HEADERS],
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
        )

    # ------------------------------------------------
    # EXPORT BAR
    # ------------------------------------------------
    def create_excel(dataframe):
        output = BytesIO()
        wb = Workbook()
        ws = wb.active

        for col, header in enumerate(KIF_HEADERS, start=1):
            ws.cell(row=1, column=col, value=header)

        for r, row in dataframe.iterrows():
            for c, header in enumerate(KIF_HEADERS, start=1):
                ws.cell(row=r+2, column=c, value=row.get(header,""))

        wb.save(output)
        return output.getvalue()

    excel = create_excel(edited_df)
    csv = edited_df.to_csv(index=False, sep=";", encoding="utf-8-sig")

    st.markdown('<div class="export-bar">', unsafe_allow_html=True)
    col1, col2 = st.columns(2)

    with col1:
        st.download_button("Preuzmi Excel", excel, "racuni.xlsx", use_container_width=True)

    with col2:
        st.download_button("Preuzmi CSV", csv, "racuni.csv", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)
