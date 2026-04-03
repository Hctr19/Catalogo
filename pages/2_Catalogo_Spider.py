import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- CLASE DEL PDF ---
class CatalogoSpider(FPDF):
    def header(self):
        self.set_fill_color(227, 29, 43)
        self.polygon([(185, 0), (210, 0), (210, 25)], fill=True)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.set_xy(198, 4)
        self.cell(10, 10, str(self.page_no()), align='C')
        self.set_text_color(50, 50, 50)
        self.set_font('Helvetica', 'B', 10)
        self.set_xy(10, 10)
        self.cell(0, 10, "CATALOGO PRODUCTOS 2026", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def draw_badge(self, text, x, y):
        self.set_font('Helvetica', 'B', 7)
        w = self.get_string_width(text) + 4
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(227, 29, 43)
        self.rect(x, y, w, 4.5, style='FD')
        self.set_text_color(50, 50, 50)
        self.text(x + 2, y + 3.5, text)
        return w + 1.5

    def añadir_producto(self, sku, nombre, detalles, url_img, comp):
        if self.get_y() > 210: self.add_page()
        y_ini = self.get_y()
        try:
            res = requests.get(url_img, timeout=5)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            self.image(img, x=10, y=y_ini + 5, w=85, h=60, keep_aspect_ratio=True)
        except: self.rect(10, y_ini + 5, 85, 60)
        
        cX = 105
        self.set_xy(cX, y_ini + 6)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(227, 29, 43)
        self.cell(0, 10, str(sku).upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if comp and str(comp).lower() != 'nan':
            currX = cX
            yB = self.get_y() + 1
            for tag in str(comp).split(','):
                currX += self.draw_badge(tag.strip(), currX, yB)
            self.set_y(yB + 8)
        self.set_x(cX); self.set_font('Helvetica', 'B', 11); self.set_text_color(0,0,0)
        self.multi_cell(95, 5, str(nombre))
        self.set_x(cX); self.set_font('Helvetica', '', 9); self.set_text_color(80,80,80)
        self.multi_cell(95, 4, str(detalles))
        self.set_y(y_ini + 75); self.set_draw_color(227, 29, 43)
        self.line(10, self.get_y(), 200, self.get_y()); self.ln(8)

# --- INTERFAZ ---
st.title("🕷️ Catálogo Formato Spider")
archivo = st.file_uploader("Sube Excel/CSV (Columnas: Sku, Nombre, Detalles, IMAGEN, Compatibilidad)", type=['csv', 'xlsx'])

if archivo:
    df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
    if st.button("🚀 Generar Spider"):
        pdf = CatalogoSpider()
        pdf.add_page()
        bar = st.progress(0)
        for i, row in df.iterrows():
            pdf.añadir_producto(row.get('Sku',''), row.get('Nombre',''), row.get('Detalles',''), row.get('IMAGEN',''), row.get('Compatibilidad',''))
            bar.progress((i+1)/len(df))
        st.download_button("⬇️ Descargar PDF", data=bytes(pdf.output()), file_name="Spider.pdf")
