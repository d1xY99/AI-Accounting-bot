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

# shadcn-style CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .block-container {
        max-width: 1100px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Header */
    .shadcn-header {
        border-bottom: 1px solid hsl(240 5.9% 90%);
        padding-bottom: 1.5rem;
        margin-bottom: 2rem;
    }
    .shadcn-header h1 {
        font-size: 1.875rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        color: hsl(240 10% 3.9%);
        margin: 0 0 0.25rem 0;
        line-height: 1.2;
    }
    .shadcn-header p {
        font-size: 0.875rem;
        color: hsl(240 3.8% 46.1%);
        margin: 0;
    }

    /* Cards */
    .shadcn-card {
        border: 1px solid hsl(240 5.9% 90%);
        border-radius: 0.75rem;
        padding: 1.5rem;
        background: white;
        margin-bottom: 1.5rem;
    }
    .shadcn-card-header {
        font-size: 1.125rem;
        font-weight: 600;
        color: hsl(240 10% 3.9%);
        letter-spacing: -0.015em;
        margin-bottom: 0.25rem;
    }
    .shadcn-card-desc {
        font-size: 0.8125rem;
        color: hsl(240 3.8% 46.1%);
        margin-bottom: 1rem;
    }

    /* Badge */
    .shadcn-badge {
        display: inline-flex;
        align-items: center;
        padding: 0.125rem 0.625rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 500;
        line-height: 1.5;
    }
    .badge-success {
        background: hsl(142 76% 94%);
        color: hsl(142 72% 29%);
        border: 1px solid hsl(142 76% 85%);
    }
    .badge-warning {
        background: hsl(48 96% 94%);
        color: hsl(32 95% 30%);
        border: 1px solid hsl(48 96% 85%);
    }
    .badge-error {
        background: hsl(0 93% 95%);
        color: hsl(0 72% 40%);
        border: 1px solid hsl(0 93% 88%);
    }
    .badge-muted {
        background: hsl(240 4.8% 95.9%);
        color: hsl(240 3.8% 46.1%);
        border: 1px solid hsl(240 5.9% 90%);
    }

    /* Status items */
    .status-item {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding: 0.625rem 0;
        border-bottom: 1px solid hsl(240 5.9% 96%);
        font-size: 0.8125rem;
    }
    .status-item:last-child { border-bottom: none; }
    .status-file {
        font-weight: 500;
        color: hsl(240 10% 3.9%);
        min-width: 120px;
    }
    .status-detail {
        color: hsl(240 3.8% 46.1%);
    }

    /* Buttons override */
    .stButton > button {
        border-radius: 0.5rem;
        font-weight: 500;
        font-size: 0.875rem;
        padding: 0.5rem 1rem;
        transition: all 0.15s ease;
        border: 1px solid hsl(240 5.9% 90%);
    }
    .stButton > button[kind="primary"] {
        background: hsl(240 5.9% 10%);
        color: white;
        border: none;
    }
    .stButton > button[kind="primary"]:hover {
        background: hsl(240 5.9% 20%);
    }
    .stButton > button:not([kind="primary"]):hover {
        background: hsl(240 4.8% 95.9%);
    }

    /* Download buttons */
    .stDownloadButton > button {
        border-radius: 0.5rem;
        font-weight: 500;
        font-size: 0.875rem;
        border: 1px solid hsl(240 5.9% 90%);
    }
    .stDownloadButton > button[kind="primary"] {
        background: hsl(240 5.9% 10%);
        color: white;
        border: none;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border-radius: 0.75rem;
    }
    [data-testid="stFileUploader"] section {
        border: 2px dashed hsl(240 5.9% 85%);
        border-radius: 0.75rem;
        padding: 2rem;
        transition: border-color 0.15s ease;
    }
    [data-testid="stFileUploader"] section:hover {
        border-color: hsl(240 5.9% 65%);
    }

    /* Data editor */
    [data-testid="stDataFrame"] {
        border: 1px solid hsl(240 5.9% 90%);
        border-radius: 0.75rem;
        overflow: hidden;
    }

    /* Progress bar */
    .stProgress > div > div {
        border-radius: 9999px;
        background-color: hsl(240 5.9% 90%);
    }
    .stProgress > div > div > div {
        border-radius: 9999px;
        background-color: hsl(240 5.9% 10%);
    }

    /* Alerts override */
    .stAlert {
        border-radius: 0.5rem;
        font-size: 0.8125rem;
        border: 1px solid;
    }

    /* Hide streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Section title */
    .section-title {
        font-size: 1.125rem;
        font-weight: 600;
        color: hsl(240 10% 3.9%);
        letter-spacing: -0.015em;
        margin-bottom: 0.25rem;
    }
    .section-desc {
        font-size: 0.8125rem;
        color: hsl(240 3.8% 46.1%);
        margin-bottom: 1rem;
    }
    .divider {
        border: none;
        border-top: 1px solid hsl(240 5.9% 90%);
        margin: 1.5rem 0;
    }

    /* Stats row */
    .stats-row {
        display: flex;
        gap: 1rem;
        margin-bottom: 1rem;
    }
    .stat-card {
        flex: 1;
        border: 1px solid hsl(240 5.9% 90%);
        border-radius: 0.75rem;
        padding: 1rem 1.25rem;
        background: white;
    }
    .stat-label {
        font-size: 0.75rem;
        font-weight: 500;
        color: hsl(240 3.8% 46.1%);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: hsl(240 10% 3.9%);
        letter-spacing: -0.025em;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="shadcn-header">
    <h1>Obrada Računa</h1>
    <p>Upload PDF račune, AI automatski izvuče podatke, preuzmi Excel tabelu.</p>
</div>
""", unsafe_allow_html=True)

# API key
api_key = ""
try:
    api_key = st.secrets.get("OPENAI_API_KEY", "")
except Exception:
    pass
if not api_key:
    api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="Unesi svoj OpenAI API ključ")

if not api_key:
    st.markdown("""
    <div class="shadcn-card">
        <div class="shadcn-card-header">API ključ potreban</div>
        <div class="shadcn-card-desc">Unesi OpenAI API ključ u sidebar-u ili ga postavi u Streamlit Cloud secrets.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Upload section
st.markdown("""
<div class="section-title">Upload</div>
<div class="section-desc">Prevuci PDF fajlove ili klikni Browse. Podržani su svi formati računa.</div>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Prevuci PDF fajlove ovdje",
    type=["pdf"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if not uploaded_files:
    st.stop()

st.markdown(f"""
<div class="stats-row">
    <div class="stat-card">
        <div class="stat-label">Odabrano fajlova</div>
        <div class="stat-value">{len(uploaded_files)}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Session state
if "results" not in st.session_state:
    st.session_state.results = []
if "processed_files" not in st.session_state:
    st.session_state.processed_files = set()

# Obradi dugme
if st.button("Obradi račune", type="primary", use_container_width=True):
    st.session_state.results = []
    st.session_state.processed_files = set()

    progress = st.progress(0, text="Pokrećem obradu...")
    status_html = []
    status_placeholder = st.empty()

    seen_numbers = set()

    for i, file in enumerate(uploaded_files):
        progress.progress(
            i / len(uploaded_files),
            text=f"Obrađujem {i+1}/{len(uploaded_files)}: {file.name}",
        )

        try:
            pdf_bytes = file.read()
            data = process_pdf(pdf_bytes, filename=file.name, api_key=api_key)

            broj = data.get("BRDOKFAKT", "")
            if broj and broj in seen_numbers:
                status_html.append(f"""
                <div class="status-item">
                    <span class="shadcn-badge badge-warning">Duplikat</span>
                    <span class="status-file">{file.name}</span>
                    <span class="status-detail">Račun {broj} već postoji</span>
                </div>""")
                status_placeholder.markdown(
                    '<div class="shadcn-card">' + "".join(status_html) + '</div>',
                    unsafe_allow_html=True,
                )
                continue

            seen_numbers.add(broj)
            st.session_state.results.append(data)
            st.session_state.processed_files.add(file.name)
            status_html.append(f"""
            <div class="status-item">
                <span class="shadcn-badge badge-success">Obrađen</span>
                <span class="status-file">{file.name}</span>
                <span class="status-detail">{data.get('NAZIVPP', '—')} · {data.get('IZNAKFT', '—')} KM</span>
            </div>""")

        except Exception as e:
            status_html.append(f"""
            <div class="status-item">
                <span class="shadcn-badge badge-error">Greška</span>
                <span class="status-file">{file.name}</span>
                <span class="status-detail">{str(e)[:80]}</span>
            </div>""")

        status_placeholder.markdown(
            '<div class="shadcn-card">' + "".join(status_html) + '</div>',
            unsafe_allow_html=True,
        )

    progress.progress(1.0, text=f"Gotovo! Obrađeno {len(st.session_state.results)} račun(a)")

# Rezultati
if st.session_state.results:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    num = len(st.session_state.results)
    total = sum(
        float(str(r.get("IZNAKFT", "0")).replace(",", ".").replace(" ", ""))
        for r in st.session_state.results
        if r.get("IZNAKFT")
    )
    total_str = f"{total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    st.markdown(f"""
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-label">Računa</div>
            <div class="stat-value">{num}</div>
        </div>
        <div class="stat-card">
            <div class="stat-label">Ukupan iznos</div>
            <div class="stat-value">{total_str} KM</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="section-title">Pregled podataka</div>
    <div class="section-desc">Klikni na polje u tabeli da ga editiraš prije downloada.</div>
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

    # Download
    st.markdown('<hr class="divider">', unsafe_allow_html=True)
    st.markdown("""
    <div class="section-title">Export</div>
    <div class="section-desc">Preuzmi podatke u željenom formatu.</div>
    """, unsafe_allow_html=True)

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
            label="Download Excel",
            data=excel_data,
            file_name="racuni.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True,
        )
    with col2:
        csv_data = edited_df.to_csv(index=False, sep=";", encoding="utf-8-sig")
        st.download_button(
            label="Download CSV",
            data=csv_data,
            file_name="racuni.csv",
            mime="text/csv",
            use_container_width=True,
        )
