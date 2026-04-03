import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Catálogo Spider", page_icon="🕷️")

ROJO_SPIDER = (227, 29, 43)
GRIS_OSCURO = (50, 50, 50)

class CatalogoSpider(FPDF):
    def header(self):
        # Triángulo rojo superior derecha
        self.set_fill_color(*ROJO_SPIDER)
        self.polygon([(185, 0), (210, 0), (210, 25)], fill=True)
        
        # Número de página
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(255, 255, 255)
        self.set_xy(198, 4)
        self.cell(10, 10, str(self.page_no()), align='C')
        
        # Encabezado
        self.set_text_color(*GRIS_OSCURO)
        self.set_font('Helvetica', 'B', 10)
        self.set_xy(10, 10)
        self.cell(0, 10, "CATALOGO PRODUCTOS 2026", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

    def draw_badge(self, text, x, y):
        self.set_font('Helvetica', 'B', 7)
        text = str(text).strip()
        w = self.get_string_width(text) + 4
        self.set_fill_color(255, 255, 255)
        self.set_draw_color(*ROJO_SPIDER)
        self.set_line_width(0.3)
        self.rect(x, y, w, 4.5, style='FD')
        self.set_text_color(*GRIS_OSCURO)
        self.text(x + 2, y + 3.5, text)
        return w + 1.5

    def añadir_producto(self, sku, nombre, detalles, url_imagen, compatibilidad):
        if self.get_y() > 210:
            self.add_page()

        y_inicio = self.get_y()
        
        # IMAGEN
        try:
            res = requests.get(url_imagen, timeout=10)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            self.image(img, x=10, y=y_inicio + 5, w=85, h=60, keep_aspect_ratio=True)
        except:
            self.set_draw_color(220, 220, 220)
            self.rect(10, y_inicio + 5, 85, 60)

        # INFORMACIÓN
        col_derecha_x = 105
        self.set_fill_color(*ROJO_SPIDER)
        self.polygon([(col_derecha_x - 4, y_inicio + 8), (col_derecha_x - 1, y_inicio + 10), (col_derecha_x - 4, y_inicio + 12)], fill=True)

        self.set_xy(col_derecha_x, y_inicio + 6)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(*ROJO_SPIDER)
        self.cell(0, 10, str(sku).upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        if compatibilidad and str(compatibilidad).lower() != 'nan':
            current_x = col_derecha_x
            y_badge = self.get_y() + 1
            for tag in str(compatibilidad).split(','):
                if tag.strip():
                    current_x += self.draw_badge(tag, current_x, y_badge)
            self.set_y(y_badge + 8)

        self.set_x(col_derecha_x)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(0, 0, 0)
        self.multi_cell(95, 5, str(nombre))

        self.set_x(col_derecha_x)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(80, 80, 80)
        self.multi_cell(95, 4, str(detalles))

        self.set_y(y_inicio + 75)
        self.set_draw_color(*ROJO_SPIDER)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(8)

# --- INTERFAZ STREAMLIT ---
st.title("🕷️ Generador de Catálogo Spider")
archivo = st.file_uploader("Sube tu archivo Excel o CSV", type=['csv', 'xlsx'])

if archivo:
    df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
    # Rellenar vacíos para evitar errores
    for col in ['Sku', 'Nombre', 'Detalles', 'IMAGEN', 'Compatibilidad']:
        if col not in df.columns: df[col] = ''
    
    st.success(f"Cargados {len(df)} productos.")

    if st.button("🚀 Generar PDF"):
        pdf = CatalogoSpider()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        progress_bar = st.progress(0)
        for i, row in df.iterrows():
            pdf.añadir_producto(row['Sku'], row['Nombre'], row['Detalles'], row['IMAGEN'], row['Compatibilidad'])
            progress_bar.progress((i + 1) / len(df))
            
        pdf_output = pdf.output()
        st.download_button("⬇️ Descargar Catálogo", data=bytes(pdf_output), file_name="Catalogo_Spider.pdf", mime="application/pdf")
