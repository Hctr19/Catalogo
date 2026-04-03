import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import time

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Generador de Catálogos Arizone", page_icon="📦")

# --- ESTILOS DE DISEÑO (IDÉNTICOS A TU ORIGINAL) ---
COLOR_FONDO = (238, 235, 227) 
COLOR_CAJA = (218, 207, 184)  
COLOR_TEXTO = (60, 60, 59)    

class CatalogoGrid(FPDF):
    def header(self):
        # Fondo de página
        self.set_fill_color(*COLOR_FONDO)
        self.rect(0, 0, 210, 297, 'F')
        
        # Marco del Título Superior
        self.set_line_width(0.5)
        self.set_draw_color(*COLOR_TEXTO)
        self.rect(40, 10, 130, 25)
        self.rect(42, 12, 126, 21) 
        
        self.set_xy(40, 15)
        self.set_font('Helvetica', 'B', 16)
        self.set_text_color(*COLOR_TEXTO)
        self.cell(130, 8, "MODELOS DISPONIBLES", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font('Helvetica', 'B', 11)
        self.cell(130, 6, "DECOFORM PREMIUM", align='C')
        
        self.ln(20)
        self.set_font('Helvetica', 'B', 14)
        self.cell(0, 10, "CATÁLOGO DE PRODUCTOS", align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(5)

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
        
        # 1. Caja Superior (SKU)
        self.set_fill_color(*COLOR_CAJA)
        self.rect(x, y, ancho_card, 6, 'F')
        self.set_xy(x, y)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*COLOR_TEXTO)
        self.cell(ancho_card, 6, str(sku), align='C')
        
        # 2. Imagen (Con manejo de errores y transparencia)
        try:
            res = requests.get(url_imagen, timeout=10)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            self.image(img, x=x, y=y + 8, w=ancho_card, h=alto_img)
        except:
            self.set_draw_color(200, 200, 200)
            self.rect(x, y + 8, ancho_card, alto_img)
            
        # 3. Caja Inferior (Nombre con Ajuste de Texto)
        y_texto = y + 8 + alto_img + 2
        self.set_fill_color(*COLOR_CAJA)
        self.rect(x, y_texto, ancho_card, alto_caja_texto, 'F')
        
        texto_limpio = str(nombre).upper()
        # Lógica de ajuste de fuente según longitud
        if len(texto_limpio) > 35:
            fuente = 6
            if len(texto_limpio) > 60: texto_limpio = texto_limpio[:57] + "..."
        elif len(texto_limpio) > 20:
            fuente = 7
        else:
            fuente = 8
            
        self.set_font('Helvetica', 'B', fuente)
        self.set_xy(x, y_texto + 1)
        self.multi_cell(ancho_card, 4, texto_limpio, align='C')

# --- LÓGICA DE LA APLICACIÓN WEB ---
st.title("📦 Generador de Catálogos Arizone")
st.write("Sube tu archivo para generar el catálogo en formato grid (3x2 por página).")

archivo = st.file_uploader("Subir archivo Excel o CSV", type=['csv', 'xlsx'])

if archivo:
    try:
        # Carga de datos
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)
            
        st.success(f"✅ Se cargaron {len(df)} productos correctamente.")
        
        # Configuración del nombre del archivo
        nombre_pdf = st.text_input("Nombre para tu PDF:", "Catalogo_Arizone")

        if st.button("🚀 Iniciar Generación de Catálogo"):
            pdf = CatalogoGrid()
            pdf.set_auto_page_break(auto=True, margin=30)
            pdf.add_page()

            x_inicial, y_inicial = 25, 65
            col_spacing, row_spacing = 55, 85
            
            # Barra de progreso
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, (index, row) in enumerate(df.iterrows()):
                # Posicionamiento 3x2
                col = i % 3
                fila = (i // 3) % 2
                
                if i > 0 and i % 6 == 0:
                    pdf.add_page()
                
                pdf.añadir_item_grid(
                    sku=row.get('Sku', row.get('SKU', 'N/A')),
                    nombre=row.get('Nombre', 'S/N'),
                    url_imagen=row.get('IMAGEN', row.get('Imagen', '')),
                    x=x_inicial + (col * col_spacing),
                    y=y_inicial + (fila * row_spacing)
                )
                
                # Actualizar progreso
                percent = (i + 1) / len(df)
                progress_bar.progress(percent)
                status_text.text(f"Procesando producto {i+1} de {len(df)}...")

            # --- CORRECCIÓN DEFINITIVA DE BYTES PARA STREAMLIT ---
            # Obtenemos la salida de fpdf2 (bytearray)
            pdf_output = pdf.output()
            
            # Convertimos estrictamente a objeto 'bytes' para el botón
            pdf_bytes = bytes(pdf_output)

            st.balloons()
            st.download_button(
                label="⬇️ DESCARGAR CATÁLOGO PDF",
                data=pdf_bytes,
                file_name=f"{nombre_pdf}.pdf",
                mime="application/pdf"
            )
            
    except Exception as e:
        st.error(f"Error crítico: {e}")
