import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from processor import process_pdf, KIF_HEADERS

# ------------------------------------------------
# PAGE
# ------------------------------------------------
st.set_page_config(page_title="BS BIRO", page_icon="📄", layout="wide")

# ------------------------------------------------
# STYLE
# ------------------------------------------------
st.markdown("""
<style>

header {visibility:hidden;}
#MainMenu {visibility:hidden;}
footer {visibility:hidden;}

.block-container {max-width:1500px;padding-top:1rem;padding-bottom:5rem;}

.title{font-size:28px;font-weight:650;letter-spacing:-0.02em;}
.subtitle{color:#6b7280;margin-top:2px;font-size:14px;}

[data-testid="stFileUploader"]{
border:2px dashed #e5e7eb;border-radius:16px;padding:60px;background:#fafafa;
}

.stDataEditor{border:1px solid #e5e7eb;border-radius:14px;overflow:hidden;}

.log-success{background:#f0fdf4;border:1px solid #bbf7d0;padding:8px 12px;border-radius:10px;margin-bottom:6px;font-size:13px;}
.log-error{background:#fef2f2;border:1px solid #fecaca;padding:8px 12px;border-radius:10px;margin-bottom:6px;font-size:13px;}
.log-warn{background:#fffbeb;border:1px solid #fde68a;padding:8px 12px;border-radius:10px;margin-bottom:6px;font-size:13px;}

.pdfbox{border:1px solid #e5e7eb;border-radius:14px;padding:6px;height:75vh;}

</style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# HEADER
# ------------------------------------------------
st.markdown("""
<div>
<div class="title">BS BIRO</div>
<div class="subtitle">Automatsko prepoznavanje podataka iz PDF računa</div>
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
if "pdf_map" not in st.session_state:
    st.session_state.pdf_map = {}
if "selected" not in st.session_state:
    st.session_state.selected = None
if "edited_table" not in st.session_state:
    st.session_state.edited_table = None

# ------------------------------------------------
# PROCESS
# ------------------------------------------------
if st.button("Obradi račune", use_container_width=True):

    st.session_state.results = []
    st.session_state.logs = []
    st.session_state.pdf_map = {}

    progress = st.progress(0)
    seen=set()

    for i,file in enumerate(uploaded_files):

        try:
            pdf_bytes=file.read()
            data=process_pdf(pdf_bytes,filename=file.name)

            broj=data.get("BRDOKFAKT","")

            if broj and broj in seen:
                st.session_state.logs.append(("warn",f"{file.name} duplikat {broj}"))
                continue

            seen.add(broj)
            st.session_state.results.append(data)
            st.session_state.pdf_map[len(st.session_state.results)-1]=pdf_bytes
            st.session_state.logs.append(("ok",f"{file.name} • {data.get('NAZIVPP','?')} • {data.get('IZNAKFT','?')} KM"))

        except Exception as e:
            st.session_state.logs.append(("err",f"{file.name} • {str(e)}"))

        progress.progress((i+1)/len(uploaded_files))

# ------------------------------------------------
# RESULTS
# ------------------------------------------------
if st.session_state.results:

    left, mid, right = st.columns([0.9,3.6,2.5])

    # ---------------- LOG ----------------
    with left:
        st.markdown("#### Status")
        st.markdown("<div style='height:72vh;overflow-y:auto'>",unsafe_allow_html=True)
        for t,msg in st.session_state.logs:
            cls={"ok":"log-success","err":"log-error","warn":"log-warn"}[t]
            st.markdown(f'<div class="{cls}">{msg}</div>',unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)

    # ---------------- TABLE ----------------
    with mid:
        st.markdown("#### Podaci")

        df=pd.DataFrame(st.session_state.results,columns=KIF_HEADERS)

        for col in KIF_HEADERS:
            if col not in df.columns:
                df[col]=""

        # dodaj preview kolonu
        df.insert(0,"Pregled",[f"R{i}" for i in range(len(df))])

        selected_row = st.radio(
            "Odaberi račun za pregled",
            options=df.index,
            format_func=lambda i: f"{df.loc[i,'NAZIVPP']} — {df.loc[i,'IZNAKFT']} KM",
            horizontal=False,
            label_visibility="collapsed"
        )

        edited_df = st.data_editor(
        df[KIF_HEADERS],
        use_container_width=True,
        hide_index=True,
        key="editor_table"
    )

    # sačuvaj uvijek zadnju verziju
    st.session_state.edited_table = edited_df

    # ---------------- PDF PREVIEW ----------------
    with right:
        st.markdown("#### Original račun")

        if selected_row is not None:
            pdf_bytes=st.session_state.pdf_map.get(selected_row)
            if pdf_bytes:
                st.download_button("Preuzmi PDF",pdf_bytes,"racun.pdf",use_container_width=True)
                st.pdf_viewer(pdf_bytes,height=720)
        else:
            st.info("Odaberi račun lijevo")

    # ------------------------------------------------
    # EXPORT
    # ------------------------------------------------
    def create_excel(dataframe):
        output=BytesIO()
        wb=Workbook()
        ws=wb.active
        for c,h in enumerate(KIF_HEADERS,1):
            ws.cell(row=1,column=c,value=h)
        for r,row in dataframe.iterrows():
            for c,h in enumerate(KIF_HEADERS,1):
                ws.cell(row=r+2,column=c,value=row.get(h,""))
        wb.save(output)
        return output.getvalue()

    export_df = st.session_state.edited_table if st.session_state.edited_table is not None else df[KIF_HEADERS]

    excel = create_excel(export_df)
    csv = export_df.to_csv(index=False, sep=";", encoding="utf-8-sig")

    st.divider()
    c1,c2=st.columns(2)
    with c1:
        st.download_button("Preuzmi Excel",excel,"racuni.xlsx",use_container_width=True)
    with c2:
        st.download_button("Preuzmi CSV",csv,"racuni.csv",use_container_width=True)
