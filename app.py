import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- CONFIGURACIÓN GENERAL ---
st.set_page_config(page_title="ARIZONE - Suite", layout="wide", initial_sidebar_state="expanded")

# --- DISEÑO 1: CLASE GRID (3x2) ---
class CatalogoGrid(FPDF):
    def header(self):
        self.set_fill_color(238, 235, 227)
        self.rect(0, 0, 210, 297, 'F')
        self.set_line_width(0.5); self.set_draw_color(60, 60, 59)
        self.rect(40, 10, 130, 25); self.rect(42, 12, 126, 21)
        self.set_xy(40, 15); self.set_font('Helvetica', 'B', 16); self.set_text_color(60, 60, 59)
        self.cell(130, 8, "MODELOS DISPONIBLES", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(20)

    def añadir_item_grid(self, sku, nombre, url_imagen, x, y):
        ancho_card, alto_img = 50, 40
        self.set_fill_color(218, 207, 184)
        self.rect(x, y, ancho_card, 6, 'F')
        self.set_xy(x, y); self.set_font('Helvetica', 'B', 9); self.cell(ancho_card, 6, str(sku), align='C')
        try:
            res = requests.get(url_imagen, timeout=5)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            self.image(img, x=x, y=y + 8, w=ancho_card, h=alto_img)
        except: self.rect(x, y + 8, ancho_card, alto_img)
        y_texto = y + 8 + alto_img + 2
        self.set_fill_color(218, 207, 184); self.rect(x, y_texto, ancho_card, 10, 'F')
        self.set_font('Helvetica', 'B', 7); self.set_xy(x, y_texto + 1)
        self.multi_cell(ancho_card, 4, str(nombre).upper()[:60], align='C')

# --- DISEÑO 2: CLASE SPIDER (LISTA) ---
class CatalogoSpider(FPDF):
    def header(self):
        self.set_fill_color(227, 29, 43); self.polygon([(185, 0), (210, 0), (210, 25)], fill=True)
        self.set_font('Helvetica', 'B', 11); self.set_text_color(255, 255, 255)
        self.set_xy(198, 4); self.cell(10, 10, str(self.page_no()), align='C')
        self.set_text_color(50, 50, 50); self.set_font('Helvetica', 'B', 10); self.set_xy(10, 10)
        self.cell(0, 10, "CATALOGO PRODUCTOS 2026", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def draw_badge(self, text, x, y):
        self.set_font('Helvetica', 'B', 7); w = self.get_string_width(text) + 4
        self.set_fill_color(255, 255, 255); self.set_draw_color(227, 29, 43)
        self.rect(x, y, w, 4.5, style='FD'); self.set_text_color(50, 50, 50)
        self.text(x + 2, y + 3.5, text); return w + 1.5

    def añadir_producto(self, sku, nombre, detalles, url_img, comp):
        if self.get_y() > 210: self.add_page()
        y_ini = self.get_y()
        try:
            res = requests.get(url_img, timeout=5)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            self.image(img, x=10, y=y_ini + 5, w=85, h=60, keep_aspect_ratio=True)
        except: self.rect(10, y_ini + 5, 85, 60)
        cX = 105; self.set_xy(cX, y_ini + 6); self.set_font('Helvetica', 'B', 20); self.set_text_color(227, 29, 43)
        self.cell(0, 10, str(sku).upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if comp and str(comp).lower() != 'nan':
            currX = cX; yB = self.get_y() + 1
            for tag in str(comp).split(','): currX += self.draw_badge(tag.strip(), currX, yB)
            self.set_y(yB + 8)
        self.set_x(cX); self.set_font('Helvetica', 'B', 11); self.set_text_color(0,0,0); self.multi_cell(95, 5, str(nombre))
        self.set_x(cX); self.set_font('Helvetica', '', 9); self.set_text_color(80,80,80); self.multi_cell(95, 4, str(detalles))
        self.set_y(y_ini + 75); self.set_draw_color(227, 29, 43); self.line(10, self.get_y(), 200, self.get_y()); self.ln(8)

# --- MENÚ LATERAL ---
st.sidebar.title("Menú de Herramientas")
modo = st.sidebar.radio("Selecciona un catálogo:", ["Inicio", "Catálogo Grid", "Catálogo Spider"])

if modo == "Inicio":
    st.title("🚀 Bienvenido a la Suite ARIZONE")
    st.info("Selecciona un formato en el menú de la izquierda para comenzar.")

elif modo == "Catálogo Grid":
    st.title("📦 Catálogo Formato Cuadrícula")
    archivo = st.file_uploader("Sube Excel/CSV (Sku, Nombre, IMAGEN)", type=['csv', 'xlsx'])
    if archivo:
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
        if st.button("🚀 Generar Grid"):
            pdf = CatalogoGrid(); pdf.add_page()
            x_ini, y_ini, c_spc, r_spc = 25, 65, 55, 85
            bar = st.progress(0)
            for i, row in df.iterrows():
                if i > 0 and i % 6 == 0: pdf.add_page()
                pdf.añadir_item_grid(row.get('Sku',''), row.get('Nombre',''), row.get('IMAGEN',''), x_ini + ((i%3)*c_spc), y_ini + (((i//3)%2)*r_spc))
                bar.progress((i+1)/len(df))
            st.download_button("⬇️ Descargar PDF", data=bytes(pdf.output()), file_name="Grid.pdf")

elif modo == "Catálogo Spider":
    st.title("🕷️ Catálogo Formato Spider")
    archivo = st.file_uploader("Sube Excel/CSV (Sku, Nombre, Detalles, IMAGEN, Compatibilidad)", type=['csv', 'xlsx'])
    if archivo:
        df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
        if st.button("🚀 Generar Spider"):
            pdf = CatalogoSpider(); pdf.add_page()
            bar = st.progress(0)
            for i, row in df.iterrows():
                pdf.añadir_producto(row.get('Sku',''), row.get('Nombre',''), row.get('Detalles',''), row.get('IMAGEN',''), row.get('Compatibilidad',''))
                bar.progress((i+1)/len(df))
            st.download_button("⬇️ Descargar PDF", data=bytes(pdf.output()), file_name="Spider.pdf")
