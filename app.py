import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Catálogos Arizone", layout="centered")

COLOR_FONDO = (238, 235, 227) 
COLOR_CAJA = (218, 207, 184)  
COLOR_TEXTO = (60, 60, 59)    

class CatalogoGrid(FPDF):
    def header(self):
        self.set_fill_color(*COLOR_FONDO)
        self.rect(0, 0, 210, 297, 'F')
        self.set_line_width(0.5)
        self.set_draw_color(*COLOR_TEXTO)
        self.rect(40, 10, 130, 25)
        self.rect(42, 12, 126, 21) 
        self.set_xy(40, 15)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*COLOR_TEXTO)
        self.cell(130, 8, "MODELOS DISPONIBLES", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(20)

    def footer(self):
        self.set_y(-25)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*COLOR_TEXTO)
        self.cell(0, 5, "DECOFORM", align='C', ln=True)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(200, 0, 0)
        self.cell(0, 5, "by ARIZONE", align='C')

    def añadir_item_grid(self, sku, nombre, url_imagen, x, y):
        ancho_card, alto_img, alto_caja_texto = 50, 40, 10
        self.set_fill_color(*COLOR_CAJA)
        self.rect(x, y, ancho_card, 6, 'F')
        self.set_xy(x, y)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*COLOR_TEXTO)
        self.cell(ancho_card, 6, str(sku), align='C')
        
        try:
            res = requests.get(url_imagen, timeout=5)
            img = Image.open(BytesIO(res.content))
            self.image(img, x=x, y=y + 8, w=ancho_card, h=alto_img)
        except:
            self.set_draw_color(200, 200, 200)
            self.rect(x, y + 8, ancho_card, alto_img)
            
        y_texto = y + 8 + alto_img + 2
        self.set_fill_color(*COLOR_CAJA)
        self.rect(x, y_texto, ancho_card, alto_caja_texto, 'F')
        texto_limpio = str(nombre).upper()
        self.set_font('Helvetica', 'B', 7 if len(texto_limpio) > 20 else 8)
        self.set_xy(x, y_texto + 1)
        self.multi_cell(ancho_card, 4, texto_limpio[:60], align='C')

# --- INTERFAZ WEB ---
st.title("📦 Creador de Catálogos PDF")
st.write("Sube tu archivo Excel o CSV para generar el catálogo automáticamente.")

archivo = st.file_uploader("Selecciona tu archivo", type=['csv', 'xlsx'])

if archivo:
    df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
    st.success(f"Archivo cargado: {len(df)} productos encontrados.")
    
    if st.button("🚀 Generar Catálogo"):
        pdf = CatalogoGrid()
        pdf.set_auto_page_break(auto=True, margin=30)
        pdf.add_page()

        x_inicial, y_inicial, col_spacing, row_spacing = 25, 65, 55, 85
        
        # Barra de progreso para muchos productos
        progress_bar = st.progress(0)
        for i, (index, row) in enumerate(df.iterrows()):
            col = i % 3
            fila = (i // 3) % 2
            if i > 0 and i % 6 == 0:
                pdf.add_page()
            
            pdf.añadir_item_grid(row['Sku'], row['Nombre'], row['IMAGEN'], 
                                x_inicial + (col * col_spacing), 
                                y_inicial + (fila * row_spacing))
            progress_bar.progress((i + 1) / len(df))

        # Descarga
        pdf_output = pdf.output(dest='S')
        st.download_button(
            label="⬇️ Descargar Catálogo PDF",
            data=pdf_output,
            file_name="Catalogo_Arizone.pdf",
            mime="application/pdf"
        )
