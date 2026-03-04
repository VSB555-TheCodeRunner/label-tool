import streamlit as st
import fitz
import numpy as np
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import io

DPI = 300
WHITE_THRESHOLD = 245


def pdf_to_image(pdf_bytes):

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(0)

    zoom = DPI / 72
    matrix = fitz.Matrix(zoom, zoom)

    pix = page.get_pixmap(matrix=matrix)

    img = Image.frombytes(
        "RGB",
        [pix.width, pix.height],
        pix.samples
    )

    doc.close()

    return img


def crop_white(img):

    arr = np.array(img)
    gray = np.mean(arr, axis=2)

    mask = gray < WHITE_THRESHOLD
    coords = np.argwhere(mask)

    if coords.size == 0:
        return img

    y0, x0 = coords.min(axis=0)
    y1, x1 = coords.max(axis=0) + 1

    return img.crop((x0, y0, x1, y1))


def build_pdf(images, labels_per_page, margin_mm, gap_mm):

    if labels_per_page == 1:
        cols, rows = 1, 1
    elif labels_per_page == 2:
        cols, rows = 1, 2
    elif labels_per_page == 4:
        cols, rows = 2, 2
    else:
        cols, rows = 2, 3

    PAGE_W, PAGE_H = A4

    margin = margin_mm * mm
    gap = gap_mm * mm

    usable_w = PAGE_W - 2 * margin - (gap if cols > 1 else 0)
    usable_h = PAGE_H - 2 * margin - (gap if rows > 1 else 0)

    cell_w = usable_w / cols
    cell_h = usable_h / rows

    buffer = io.BytesIO()

    c = canvas.Canvas(buffer, pagesize=A4)

    idx = 0

    for r in range(rows):
        for col in range(cols):

            if idx >= labels_per_page:
                break

            img = images[idx % len(images)]

            img_reader = ImageReader(img)

            x = margin + col * (cell_w + (gap if col > 0 else 0))
            y = PAGE_H - margin - (r + 1) * cell_h - (gap if r > 0 else 0)

            c.drawImage(
                img_reader,
                x,
                y,
                width=cell_w,
                height=cell_h,
                preserveAspectRatio=False
            )

            idx += 1

    c.showPage()
    c.save()

    buffer.seek(0)

    return buffer


st.title("Label to A4 Generator")

st.write("Upload label PDFs and generate A4 sheet")

uploaded_files = st.file_uploader(
    "Upload Label PDF(s)",
    type="pdf",
    accept_multiple_files=True
)

labels_per_page = st.selectbox(
    "Labels per A4",
    [1,2,4,6]
)

margin_mm = st.slider(
    "Outer Margin (mm)",
    0.0,
    10.0,
    2.5
)

gap_mm = st.slider(
    "Center Gap (mm)",
    0.0,
    10.0,
    4.0
)

if uploaded_files:

    images = []

    for file in uploaded_files:

        img = pdf_to_image(file.read())
        img = crop_white(img)

        images.append(img)

    if st.button("Generate A4 PDF"):

        pdf_buffer = build_pdf(
            images,
            labels_per_page,
            margin_mm,
            gap_mm
        )

        st.success("PDF generated!")

        st.download_button(
            label="Download PDF",
            data=pdf_buffer,
            file_name="labels_output.pdf",
            mime="application/pdf"
        )