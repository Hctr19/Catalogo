import streamlit as st
import pandas as pd
import requests
import os
import math
import zipfile
import textwrap
from io import BytesIO

# --- LIBRERÍAS DE DISEÑO ---
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="ARIZONE - Suite", layout="wide")

# Rutas de las fuentes en el repositorio
FONT_BOLD_PATH = "Arial Bold.ttf"
FONT_REG_PATH = "Arial Bold.ttf" 

# ==========================================
# 1. DISEÑOS PDF (GRID Y LISTA) - UNICODE OK
# ==========================================

class CatalogoGrid(FPDF):
    def __init__(self):
        super().__init__()
        try:
            self.add_font("ArialCustom", "", FONT_REG_PATH)
            self.add_font("ArialCustom", "B", FONT_BOLD_PATH)
            self.fuente_pdf = "ArialCustom"
        except:
            self.fuente_pdf = "Helvetica"

    def header(self):
        self.set_fill_color(238, 235, 227); self.rect(0, 0, 210, 297, 'F')
        self.set_line_width(0.5); self.set_draw_color(60, 60, 59)
        self.rect(40, 10, 130, 25); self.rect(42, 12, 126, 21)
        self.set_xy(40, 15); self.set_font(self.fuente_pdf, 'B', 16); self.set_text_color(60, 60, 59)
        self.cell(130, 8, "MODELOS DISPONIBLES", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def añadir_item_grid(self, sku, nombre, url_imagen, x, y):
        ancho_card, alto_img = 50, 40
        self.set_fill_color(218, 207, 184); self.rect(x, y, ancho_card, 6, 'F')
        self.set_xy(x, y); self.set_font(self.fuente_pdf, 'B', 9); self.cell(ancho_card, 6, str(sku), align='C')
        try:
            res = requests.get(url_imagen, timeout=5)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            self.image(img, x=x, y=y + 8, w=ancho_card, h=alto_img)
        except: self.rect(x, y + 8, ancho_card, alto_img)
        y_texto = y + 8 + alto_img + 2
        self.set_fill_color(218, 207, 184); self.rect(x, y_texto, ancho_card, 10, 'F')
        self.set_font(self.fuente_pdf, 'B', 7); self.set_xy(x, y_texto + 1)
        self.multi_cell(ancho_card, 4, str(nombre).upper()[:60], align='C')

class CatalogoLista(FPDF):
    def __init__(self):
        super().__init__()
        try:
            self.add_font("ArialCustom", "", FONT_REG_PATH)
            self.add_font("ArialCustom", "B", FONT_BOLD_PATH)
            self.fuente_pdf = "ArialCustom"
        except:
            self.fuente_pdf = "Helvetica"

    def header(self):
        self.set_fill_color(227, 29, 43); self.polygon([(185, 0), (210, 0), (210, 25)], fill=True)
        self.set_font(self.fuente_pdf, 'B', 11); self.set_text_color(255, 255, 255)
        self.set_xy(198, 4); self.cell(10, 10, str(self.page_no()), align='C')
        self.set_text_color(50, 50, 50); self.set_font(self.fuente_pdf, 'B', 10); self.set_xy(10, 10)
        self.cell(0, 10, "CATALOGO PRODUCTOS 2026", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def añadir_producto(self, sku, nombre, url_img):
        if self.get_y() > 210: self.add_page()
        y_ini = self.get_y()
        try:
            res = requests.get(url_img, timeout=5)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            self.image(img, x=10, y=y_ini + 5, w=85, h=60, keep_aspect_ratio=True)
        except: self.rect(10, y_ini + 5, 85, 60)
        cX = 105; self.set_xy(cX, y_ini + 6); self.set_font(self.fuente_pdf, 'B', 20); self.set_text_color(227, 29, 43)
        self.cell(0, 10, str(sku).upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(cX); self.set_font(self.fuente_pdf, 'B', 11); self.set_text_color(0,0,0); self.multi_cell(95, 5, str(nombre))
        self.set_y(y_ini + 75); self.set_draw_color(227, 29, 43); self.line(10, self.get_y(), 200, self.get_y()); self.ln(8)

# ==========================================
# 2. DISEÑO 3x3 PRO (REPORTLAB)
# ==========================================

def generar_pdf_3x3_original(df, imagen_fondo=None):
    output = BytesIO()
    c = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    fondo_reader = ImageReader(imagen_fondo) if imagen_fondo else None

    try:
        pdfmetrics.registerFont(TTFont('Arial-Bold', FONT_BOLD_PATH))
        f_bold = "Arial-Bold"
    except:
        f_bold = "Helvetica-Bold"

    cols, rows, margin, padding = 3, 3, 1 * cm, 0.35 * cm
    cell_w, cell_h = (width - 2*margin)/cols, (height - 2*margin)/rows
    style_nombre = ParagraphStyle('NombreStyle', fontSize=8, leading=9.5, textColor=colors.black, fontName=f_bold)

    for i, row in df.iterrows():
        idx = i % 9
        if idx == 0:
            if fondo_reader: c.drawImage(fondo_reader, 0, 0, width=width, height=height)
            else: c.setFillColor(colors.white); c.rect(0, 0, width, height, fill=1)
            c.setFillColor(colors.HexColor("#333333")); c.roundRect(0.8*cm, height-1.2*cm, 5.5*cm, 0.7*cm, 3, fill=1)
            c.setFillColor(colors.white); c.setFont(f_bold, 10); c.drawCentredString(3.55*cm, height-0.95*cm, "PRODUCTOS DISPONIBLES")
            c.setFillColor(colors.black); c.setFont("Helvetica", 9); c.drawRightString(width-1*cm, 0.5*cm, f"Página { (i//9)+1 }")

        col, fil = idx % cols, rows - 1 - (idx // cols)
        x_base, y_base = margin + (col * cell_w), margin + (fil * cell_h)
        c.setStrokeColor(colors.black); c.setLineWidth(0.4); c.setFillColor(colors.white)
        c.rect(x_base+3, y_base+3, cell_w-6, cell_h-6, fill=1, stroke=1)
        
        x, y, w, h = x_base+padding, y_base+padding, cell_w-(2*padding), cell_h-(2*padding)
        try:
            img = ImageReader(BytesIO(requests.get(row['IMAGEN'], timeout=10).content))
            c.drawImage(img, x, y + (h*0.42), width=w, height=h*0.55, preserveAspectRatio=True, anchor='c')
        except: pass

        c.setFont(f_bold, 9); c.setFillColor(colors.black); c.drawString(x, y + (h*0.36), str(row['Sku']))
        
        # Unificación: PRECIO 1 (Limpieza de doble $)
        precio_val = str(row.get('PRECIO 1', '0')).replace('$', '').strip()
        precio_texto = f"$ {precio_val}"
        
        c.setFont(f_bold, 10); tw = c.stringWidth(precio_texto, f_bold, 10)
        c.setFillColor(colors.red); c.roundRect(x, y+8, tw+8, 14, 2, fill=1)
        c.setFillColor(colors.white); c.drawString(x+4, y+11.5, precio_texto)
        c.setFillColor(colors.black); c.setFont("Helvetica", 7); c.drawRightString(x+w, y+11.5, f"Stock: {row['Almacen']}")
        p = Paragraph(str(row['Nombre']), style_nombre); p_w, p_h = p.wrap(w, (y+(h*0.36))-(y+26)); p.drawOn(c, x, (y+(h*0.36))-p_h-2)
        if (i+1) % 9 == 0: c.showPage()
    
    c.save(); return output.getvalue()

# ==========================================
# 3. VOLANTES PNG (PILLOW)
# ==========================================

def get_image(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10)
        return Image.open(BytesIO(res.content)).convert("RGBA")
    except: return None

def draw_product_card(draw, img_canvas, row, x, y):
    card_w, card_h = 330, 400
    x0, y0 = x - card_w // 2, y - card_h // 2
    draw.rectangle([x0, y0, x0+card_w, y0+card_h], fill=(255, 255, 255), outline=(220, 220, 220), width=1)
    
    try:
        f_sku = ImageFont.truetype(FONT_BOLD_PATH, 18)
        f_price = ImageFont.truetype(FONT_BOLD_PATH, 22) 
        f_name_base = ImageFont.truetype(FONT_BOLD_PATH, 13)
    except:
        f_sku = f_price = f_name_base = ImageFont.load_default()

    p_img = get_image(row['IMAGEN'])
    if p_img:
        p_img.thumbnail((280, 240))
        img_canvas.paste(p_img, (x - p_img.width // 2, y0 + 30), p_img if p_img.mode == 'RGBA' else None)

    y_start = y0 + card_h - 85
    
    # Unificación: PRECIO 1 (Limpieza de doble $)
    precio_raw = str(row.get('PRECIO 1', '0')).replace('$', '').strip()
    price_str = f"$ {precio_raw}"
    
    price_w = draw.textlength(price_str, font=f_price) + 16 
    price_h = 48 
    px0, py0 = x0 + 15, y_start

    draw.rectangle([px0, py0, px0 + price_w, py0 + price_h], fill=(227, 29, 43))
    draw.text((px0 + price_w/2, py0 + price_h/2), price_str, fill="white", font=f_price, anchor="mm")

    text_x = px0 + price_w + 12
    draw.text((text_x, y_start + 2), str(row['Sku']), fill=(50, 50, 50), font=f_sku)
    nombre_raw = str(row['Nombre']).upper()
    nombre_wrap = textwrap.wrap(nombre_raw, width=20)
    current_y = y_start + 24
    for line in nombre_wrap[:3]:
        draw.text((text_x, current_y), line, fill=(0,0,0), font=f_name_base)
        current_y += 16

def generate_grid_flyer(df_chunk):
    W, H = 1080, 1080
    img = Image.new('RGB', (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try: f_title = ImageFont.truetype(FONT_BOLD_PATH, 60); f_footer = ImageFont.truetype(FONT_BOLD_PATH, 18)
    except: f_title = f_footer = ImageFont.load_default()
    draw.rectangle([210, 35, 870, 115], fill=(227, 29, 43))
    draw.text((540, 75), "PROMOCIONES ACTIVAS", fill="white", font=f_title, anchor="mm")
    POSS = [(185, 360), (540, 360), (895, 360), (185, 780), (540, 780), (895, 780)]
    for i, (idx, row) in enumerate(df_chunk.iterrows()):
        if i < 6: draw_product_card(draw, img, row, POSS[i][0], POSS[i][1])
    draw.text((540, 1045), "VIGENCIA HASTA AGOTAR EXISTENCIAS | ARIZONE AUTO PARTS", fill=(130, 130, 130), font=f_footer, anchor="mm")
    return img

# ==========================================
# 4. INTERFAZ STREAMLIT
# ==========================================

st.sidebar.title("ARIZONE Suite")
opcion = st.sidebar.radio("Herramientas:", ["Inicio", "Catálogo Cuadrícula", "Catálogo Lista", "Catálogo 3x3 Pro", "Volantes Social Media"])

if opcion == "Inicio":
    st.title("🚀 Suite ARIZONE")
    st.markdown("---")
    st.write("Columnas requeridas en el archivo:")
    st.code("Sku, Nombre, Almacen, IMAGEN, PRECIO 1")

else:
    col1, col2 = st.columns([2, 1])
    with col1:
        archivo = st.file_uploader("1. Sube tu CSV o Excel", type=['csv', 'xlsx'])
    
    imagen_fondo = None
    if opcion == "Catálogo 3x3 Pro":
        with col2:
            img_upload = st.file_uploader("2. Fondo (Opcional)", type=['png', 'jpg', 'jpeg'])
            if img_upload:
                imagen_fondo = BytesIO(img_upload.read())
                st.image(imagen_fondo, caption="Fondo", width=100)

    if archivo:
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
        
        if opcion == "Catálogo Cuadrícula":
            if st.button("Generar PDF"):
                pdf = CatalogoGrid(); pdf.add_page()
                for i, row in df.iterrows():
                    if i > 0 and i % 6 == 0: pdf.add_page()
                    pdf.añadir_item_grid(row['Sku'], row['Nombre'], row['IMAGEN'], 25+((i%3)*55), 65+(((i//3)%2)*85))
                st.download_button("Descargar", bytes(pdf.output()), "Grid_3x2.pdf")

        elif opcion == "Catálogo Lista":
            if st.button("Generar PDF"):
                pdf = CatalogoLista(); pdf.add_page()
                for i, row in df.iterrows():
                    pdf.añadir_producto(row['Sku'], row['Nombre'], row['IMAGEN'])
                st.download_button("Descargar", bytes(pdf.output()), "Lista.pdf")

        elif opcion == "Catálogo 3x3 Pro":
            if st.button("Generar PDF"):
                pdf_data = generar_pdf_3x3_original(df, imagen_fondo)
                st.download_button("Descargar", pdf_data, "3x3_Pro.pdf")

        elif opcion == "Volantes Social Media":
            if st.button("Generar Volantes"):
                zip_buf = BytesIO()
                with zipfile.ZipFile(zip_buf, "a", zipfile.ZIP_DEFLATED) as zip_file:
                    for i in range(0, len(df), 6):
                        img = generate_grid_flyer(df.iloc[i:i+6])
                        buf = BytesIO(); img.save(buf, format='PNG')
                        zip_file.writestr(f"volante_{i//6 + 1}.png", buf.getvalue())
                st.download_button("Descargar ZIP", zip_buf.getvalue(), "Volantes_Arizone.zip")
