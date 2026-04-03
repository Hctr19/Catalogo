import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- CLASE DEL PDF ---
class CatalogoGrid(FPDF):
    def header(self):
        self.set_fill_color(238, 235, 227) 
        self.rect(0, 0, 210, 297, 'F')
        self.set_line_width(0.5)
        self.set_draw_color(60, 60, 59)
        self.rect(40, 10, 130, 25)
        self.rect(42, 12, 126, 21) 
        self.set_xy(40, 15)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(60, 60, 59)
        self.cell(130, 8, "MODELOS DISPONIBLES", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(20)

    def footer(self):
        self.set_y(-25)
        self.set_font('Helvetica', 'B', 9)
        self.cell(0, 5, "DECOFORM by ARIZONE", align='C')

    def añadir_item_grid(self, sku, nombre, url_imagen, x, y):
        ancho_card, alto_img = 50, 40
        self.set_fill_color(218, 207, 184)
        self.rect(x, y, ancho_card, 6, 'F')
        self.set_xy(x, y)
        self.set_font('Helvetica', 'B', 9)
        self.cell(ancho_card, 6, str(sku), align='C')
        try:
            res = requests.get(url_imagen, timeout=5)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            self.image(img, x=x, y=y + 8, w=ancho_card, h=alto_img)
        except:
            self.rect(x, y + 8, ancho_card, alto_img)
        y_texto = y + 8 + alto_img + 2
        self.set_fill_color(218, 207, 184)
        self.rect(x, y_texto, ancho_card, 10, 'F')
        self.set_font('Helvetica', 'B', 7)
        self.set_xy(x, y_texto + 1)
        self.multi_cell(ancho_card, 4, str(nombre).upper()[:60], align='C')

# --- INTERFAZ ---
st.title("📦 Catálogo Formato Cuadrícula")
archivo = st.file_uploader("Sube Excel/CSV (Columnas: Sku, Nombre, IMAGEN)", type=['csv', 'xlsx'])

if archivo:
    df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
    if st.button("🚀 Generar Grid"):
        pdf = CatalogoGrid()
        pdf.add_page()
        x_ini, y_ini, c_spc, r_spc = 25, 65, 55, 85
        bar = st.progress(0)
        for i, row in df.iterrows():
            if i > 0 and i % 6 == 0: pdf.add_page()
            pdf.añadir_item_grid(row.get('Sku',''), row.get('Nombre',''), row.get('IMAGEN',''), 
                                x_ini + ((i%3)*c_spc), y_ini + (((i//3)%2)*r_spc))
            bar.progress((i+1)/len(df))
        st.download_button("⬇️ Descargar PDF", data=bytes(pdf.output()), file_name="Grid.pdf")
