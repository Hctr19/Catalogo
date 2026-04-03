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

# --- ESTILOS DE DISEÑO ---
COLOR_FONDO = (238, 235, 227) 
COLOR_CAJA = (218, 207, 184)  
COLOR_TEXTO = (60, 60, 59)    

class CatalogoGrid(FPDF):
    def header(self):
        # Fondo de página
        self.set_fill_color(*COLOR_FONDO)
        self.rect(0, 0, 210, 297, 'F')
        
        # Marco del Título
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
        
        # 1. Caja SKU
        self.set_fill_color(*COLOR_CAJA)
        self.rect(x, y, ancho_card, 6, 'F')
        self.set_xy(x, y)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*COLOR_TEXTO)
        self.cell(ancho_card, 6, str(sku), align='C')
        
        # 2. Imagen
        try:
            res = requests.get(url_imagen, timeout=10)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            self.image(img, x=x, y=y + 8, w=ancho_card, h=alto_img)
        except:
            self.set_draw_color(200, 200, 200)
            self.rect(x, y + 8, ancho_card, alto_img)
            
        # 3. Caja Nombre
        y_texto = y + 8 + alto_img + 2
        self.set_fill_color(*COLOR_CAJA)
        self.rect(x, y_texto, ancho_card, alto_caja_texto, 'F')
        
        texto_limpio = str(nombre).upper()
        # Ajuste dinámico de fuente
        fuente = 8
        if len(texto_limpio) > 35: fuente = 6
        elif len(texto_limpio) > 20: fuente = 7
            
        self.set_font('Helvetica', 'B', fuente)
        self.set_xy(x, y_texto + 1)
        self.multi_cell(ancho_card, 4, texto_limpio[:60], align='C')

# --- INTERFAZ DE USUARIO ---
st.title("📦 Generador de Catálogos Arizone")
st.markdown("""
Sube tu archivo **CSV** o **Excel** con las columnas `Sku`, `Nombre` e `IMAGEN`. 
La aplicación generará un grid de 3x2 por página automáticamente.
""")

archivo = st.file_uploader("Subir archivo de datos", type=['csv', 'xlsx'])

if archivo:
    try:
        if archivo.name.endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            df = pd.read_excel(archivo)
            
        st.success(f"✅ Se cargaron {len(df)} productos correctamente.")
        
        # Opciones adicionales
        with st.expander("Configuración avanzada"):
            nombre_final = st.text_input("Nombre del archivo PDF", "Catalogo_Arizone")
            procesar_todo = st.checkbox("Procesar todos los productos", value=True)
            if not procesar_todo:
                cantidad = st.slider("Cantidad de productos a procesar", 1, len(df), 10)
                df = df.head(cantidad)

        if st.button("🚀 Generar PDF Ahora"):
            pdf = CatalogoGrid()
            pdf.set_auto_page_break(auto=True, margin=30)
            pdf.add_page()

            x_inicial, y_inicial = 25, 65
            col_spacing, row_spacing = 55, 85
            
            progress_text = "Descargando imágenes y armando el grid..."
            bar = st.progress(0, text=progress_text)
            
            for i, (index, row) in enumerate(df.iterrows()):
                col = i % 3
                fila = (i // 3) % 2
                
                if i > 0 and i % 6 == 0:
                    pdf.add_page()
                
                pdf.añadir_item_grid(
                    sku=row.get('Sku', 'N/A'),
                    nombre=row.get('Nombre', 'S/N'),
                    url_imagen=row.get('IMAGEN', ''),
                    x=x_inicial + (col * col_spacing),
                    y=y_inicial + (fila * row_spacing)
                )
                
                # Actualizar barra de progreso
                percent = (i + 1) / len(df)
                bar.progress(percent, text=f"Procesando {i+1} de {len(df)} productos...")

            # GENERACIÓN DE BYTES (CORRECCIÓN DE ERROR)
            pdf_bytes = pdf.output() # fpdf2 devuelve bytes por defecto
            
            st.balloons()
            st.download_button(
                label="⬇️ DESCARGAR CATÁLOGO PDF",
                data=pdf_bytes,
                file_name=f"{nombre_final}.pdf",
                mime="application/pdf"
            )
            
    except Exception as e:
        st.error(f"Hubo un error al procesar el archivo: {e}")
