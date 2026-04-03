import streamlit as st

st.set_page_config(
    page_title="ARIZONE - Suite de Catálogos",
    page_icon="🛠️",
    layout="wide"
)

st.title("🚀 Bienvenido a la Suite de Herramientas ARIZONE")
st.markdown("---")

st.info("""
### ⬅️ Selecciona una herramienta en el menú de la izquierda para comenzar:

1.  **Catálogo Cuadrícula (Grid):** * Ideal para volúmenes grandes (1000+ productos).
    * Formato de 3 columnas x 2 filas (6 productos por página).
    * Diseño limpio y minimalista.

2.  **Catálogo Detallado (Gral):**
    * Ideal para productos técnicos.
    * Formato de lista vertical (3 productos por página).
    * Incluye "Badges" de **Compatibilidad** y descripciones largas.
""")

st.write("---")
st.caption("Desarrollado para la gestión eficiente de catálogos Arizone.")
