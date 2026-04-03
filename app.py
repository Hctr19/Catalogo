import streamlit as st
import pandas as pd
import requests
from io import BytesIO
from PIL import Image
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="ARIZONE - Suite", layout="wide")

# --- SELECTOR MANUAL EN LA BARRA LATERAL ---
st.sidebar.title("Menú de Herramientas")
modo = st.sidebar.radio("Selecciona un catálogo:", ["Inicio", "Catálogo Grid", "Catálogo Spider"])

if modo == "Inicio":
    st.title("🚀 Bienvenido a la Suite ARIZONE")
    st.info("Selecciona un formato en el menú de la izquierda para comenzar.")

elif modo == "Catálogo Grid":
    st.title("📦 Catálogo Formato Cuadrícula")
    # Pega aquí TODO el código que tenías en 1_Catalogo_Grid.py (empezando por la clase CatalogoGrid)
    st.write("Sube tu archivo para el diseño Grid...")

elif modo == "Catálogo Spider":
    st.title("🕷️ Catálogo Formato Spider")
    # Pega aquí TODO el código que tenías en 2_Catalogo_Spider.py (empezando por la clase CatalogoSpider)
    st.write("Sube tu archivo para el diseño Spider...")
