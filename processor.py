import openai
import base64
import json
import random
import fitz
from pdf2image import convert_from_path
from io import BytesIO
import tempfile
import os

MIN_TEXT_LENGTH = 100

KIF_HEADERS = [
    "REDBR", "TIPDOK", "BRDOKFAKT", "DATUMF",
    "NAZIVPP", "SJEDISTEPP", "IDDVPP", "JIBPUPP",
    "IZNAKFT", "IZNOSNOV", "IZNPDV",
]

POZNATI_PARTNERI = [
    #todo
]

EXTRACTION_PROMPT = """Ovo je račun/faktura. Izvuci polja i vrati kao JSON objekat.

Ključevi MORAJU biti TAČNO ovi (ostavi prazan string "" ako ne postoji):

{
  "BRDOKFAKT": "Broj računa/fakture (npr. 432/10, 9034508513, 600398-1-0126-1)",
  "DATUMF": "Datum izdavanja fakture (format DD.MM.GGGG)",
  "NAZIVPP": "Puni naziv KUPCA - firma KOJOJ je račun izdat (ne firma koja izdaje račun!)",
  "SJEDISTEPP": "Puna adresa kupca sa poštanskim brojem i mjestom",
  "IDDVPP": "ID broj (JIB) kupca - MORA biti TAČNO 13 cifara i počinjati sa 4. Ako na računu vidiš broj koji nema 13 cifara ili ne počinje sa 4, dodaj vodeću 4 da bude 13 cifara",
  "JIBPUPP": "PDV broj kupca - MORA biti TAČNO 12 cifara. To je isti broj kao ID/JIB ali BEZ vodeće cifre 4. Ako kupac NIJE u PDV sistemu (nema PDV broj na računu), ostavi prazan string",
  "IZNOSNOV": "Iznos BEZ PDV-a (decimalni separator zarez, npr. 155,87)",
  "IZNPDV": "Iznos PDV-a u KM (NE procenat, nego koliko PDV iznosi u novcu, npr. 26,50)",
  "IZNAKFT": "UKUPAN iznos za uplatu SA PDV-om (npr. 182,37)"
}

VAŽNO:
- Vrati SAMO čist JSON objekat (NE niz), bez markdown, bez objašnjenja
- Ovo je jedan račun - vrati jedan JSON objekat
- KUPAC je firma na koju glasi račun (piše "Korisnik:", "Kupac:", "Za:" ili slično)
- DOBAVLJAČ/IZDAVAČ je firma čiji je logo/zaglavlje (firma koja ŠALJE račun) - to NIJE kupac!
- Koristi zarez kao decimalni separator (npr. 102,70)
- Datum u formatu DD.MM.GGGG
- ID broj (JIB) = 13 cifara, počinje sa 4
- PDV broj = 12 cifara, isti kao JIB bez vodeće 4 (samo firme u PDV sistemu)
- IZNPDV je iznos u KM, NE procenat
- Brojeve prepiši TAČNO
"""


def split_pdf_to_pages(pdf_bytes):
    """Razdvaja multi-page PDF na listu single-page PDF bajtova."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page_num in range(len(doc)):
        single = fitz.open()
        single.insert_pdf(doc, from_page=page_num, to_page=page_num)
        pages.append((page_num + 1, single.tobytes()))
        single.close()
    doc.close()
    return pages


def extract_text_from_bytes(pdf_bytes):
    """Izvlači ugrađeni tekst iz PDF bajtova."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


def pdf_bytes_to_images_base64(pdf_bytes):
    """Konvertuje PDF bajtove u base64 slike."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        pages = convert_from_path(tmp_path, dpi=200)
        images = []
        for page in pages:
            buffer = BytesIO()
            page.save(buffer, format="PNG")
            img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
            images.append(img_base64)
        return images
    finally:
        os.unlink(tmp_path)


def validate_id_pdv(data):
    """Validacija i korekcija IDDVPP (13 cifara) i JIBPUPP (12 cifara)."""
    id_broj = str(data.get("IDDVPP", "")).strip().replace(" ", "")
    if id_broj:
        if len(id_broj) == 12 and not id_broj.startswith("4"):
            id_broj = "4" + id_broj
        if len(id_broj) == 13 and id_broj.startswith("4"):
            data["IDDVPP"] = id_broj
            pdv = str(data.get("JIBPUPP", "")).strip()
            if not pdv:
                data["JIBPUPP"] = id_broj[1:]
            elif len(pdv) != 12:
                data["JIBPUPP"] = id_broj[1:]
    return data


def process_pdf(pdf_bytes, filename="", api_key=None):
    """Obrađuje PDF i vraća dict sa KIF podacima."""
    client = openai.OpenAI(api_key=api_key)

    pdf_text = extract_text_from_bytes(pdf_bytes)

    content = []
    has_text = len(pdf_text) >= MIN_TEXT_LENGTH
    images = pdf_bytes_to_images_base64(pdf_bytes)

    for img in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"},
        })

    if has_text:
        content.append({
            "type": "text",
            "text": f"Pogledaj SLIKU da razumiješ raspored - ko je kupac a ko dobavljač.\n"
                    f"DOBAVLJAČ/IZDAVAČ je firma čiji je logo/zaglavlje (firma koja ŠALJE račun).\n"
                    f"KUPAC je firma na koju glasi račun (piše 'Korisnik:', 'Kupac:' ili slično).\n\n"
                    f"Za TAČNE brojeve koristi ovaj tekst iz PDF-a:\n\n"
                    f"---\n{pdf_text}\n---\n\n{EXTRACTION_PROMPT}",
        })
    else:
        content.append({"type": "text", "text": EXTRACTION_PROMPT})

    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.choices[0].message.content.strip()

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        raw = raw.rsplit("```", 1)[0]

    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start >= 0 and end > start:
        raw = raw[start:end]

    data = json.loads(raw)

    # Dopuni iz poznatih partnera
    full_text = (pdf_text + " " + json.dumps(data)).lower()
    for partner in POZNATI_PARTNERI:
        if any(kw.lower() in full_text for kw in partner["kljucne_rijeci"]):
            if not data.get("NAZIVPP"):
                data["NAZIVPP"] = partner["naziv"]
            if not data.get("IDDVPP"):
                data["IDDVPP"] = partner["id"]
            if not data.get("JIBPUPP"):
                data["JIBPUPP"] = partner["pdv"]
            if not data.get("SJEDISTEPP"):
                data["SJEDISTEPP"] = partner["adresa"]
            break

    # Validacija ID/PDV
    data = validate_id_pdv(data)

    # Fiksna polja
    data["REDBR"] = random.randint(1, 10)
    data["TIPDOK"] = "01"

    # Konvertuj brojeve u string sa zarezom
    for key in ["IZNAKFT", "IZNOSNOV", "IZNPDV"]:
        val = data.get(key, "")
        if isinstance(val, (int, float)):
            data[key] = f"{val:.2f}".replace(".", ",")

    return data


def process_multi_page_pdf(pdf_bytes, filename="", api_key=None):
    """Razdvaja PDF po stranicama i obrađuje svaku kao zaseban račun."""
    pages = split_pdf_to_pages(pdf_bytes)
    results = []
    for page_num, page_bytes in pages:
        data = process_pdf(page_bytes, filename=f"{filename} (str. {page_num})", api_key=api_key)
        data["_page_num"] = page_num
        data["_page_bytes"] = page_bytes
        results.append(data)
    return results
