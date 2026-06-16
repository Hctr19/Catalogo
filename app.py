import streamlit as st
import pandas as pd
import requests
import json
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
st.set_page_config(page_title="ARIZONE - Multi App 2026", layout="wide")

# Ruta de la fuente
FONT_BOLD_PATH = "Arial Bold.ttf"

# --- NUEVA FUNCIÓN PARA PROCESAR DIRECCIONES CON GEMINI ---
def limpiar_telefono_10_digitos(tel):
    if not tel:
        return "8330000000"
    num = "".join(c for c in str(tel) if c.isdigit())
    if len(num) == 10:
        return num
    elif len(num) > 10:
        return num[-10:]
    else:
        return (num + "0000000000")[:10]

def parsear_direccion_con_ia(texto_libre, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    prompt = f"""
    Analiza el siguiente texto que contiene una dirección de destino para un envío y extrae la información en un formato JSON estrictamente limpio. 
    Si algún dato no viene en el texto, déjalo como una cadena vacía "". No inventes datos.
    
    Texto del cliente: "{texto_libre}"
    
    El formato JSON debe ser exactamente con estas llaves obligatorias:
    {{
      "name": "Nombre completo de la persona",
      "phone": "Teléfono a 10 dígitos (solo números)",
      "street": "Nombre de la calle",
      "number": "Número exterior",
      "interiorNumber": "Número interior o departamento",
      "district": "Colonia",
      "city": "Ciudad o Municipio",
      "state": "Código de 2 letras del Estado (ej: TM, NL, JC, CX)",
      "zipCode": "Código Postal de 5 dígitos",
      "reference": "Referencias adicionales de la casa/entre calles"
    }}
    Devuelve ÚNICAMENTE el JSON estructurado, sin bloques de código Markdown (sin ```json) ni texto explicativo.
    """
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        if res.status_code == 200:
            resultado = res.json()
            texto_respuesta = resultado['candidates'][0]['content']['parts'][0]['text'].strip()
            # Limpiar por si acaso la IA ignora la instrucción de omitir markdown
            if "```" in texto_respuesta:
                parts = texto_respuesta.split("```")
                for part in parts:
                    part_clean = part.strip()
                    if part_clean.startswith("json"):
                        part_clean = part_clean[4:].strip()
                    if part_clean.startswith("{") and part_clean.endswith("}"):
                        texto_respuesta = part_clean
                        break
            else:
                texto_respuesta = texto_respuesta.strip()
            return json.loads(texto_respuesta)
    except Exception as e:
        st.error(f"Error al procesar con la IA: {e}")
    return None

# --- LÓGICA DE AUTORELLENO DE ESTADOS (MÉXICO) ---
def obtener_estado_por_cp(cp):
    if not cp or len(cp) < 2: return ""
    prefijo = cp[:2]
    mapeo = {
        "01": "CX", "02": "CX", "03": "CX", "04": "CX", "05": "CX", "06": "CX", "07": "CX", "08": "CX", "09": "CX", "10": "CX", "11": "CX", "12": "CX", "13": "CX", "14": "CX", "15": "CX", "16": "CX",
        "20": "AG", "21": "BC", "22": "BC", "23": "BS", "24": "CM", "29": "CH", "30": "CH", "31": "CH", "32": "CH", "33": "CH", "34": "DG", "35": "DG", "36": "GT", "37": "GT", "38": "GT", "39": "GR",
        "40": "GR", "41": "GR", "42": "HG", "43": "HG", "44": "JC", "45": "JC", "46": "JC", "47": "JC", "48": "JC", "49": "JC", "50": "EM", "51": "EM", "52": "EM", "53": "EM", "54": "EM", "55": "EM", "56": "EM", "57": "EM",
        "58": "MI", "59": "MI", "60": "MI", "61": "MI", "62": "MO", "63": "NA", "64": "NL", "65": "NL", "66": "NL", "67": "NL", "68": "OA", "69": "OA", "70": "OA", "71": "OA", "72": "PU", "73": "PU", "74": "PU", "75": "PU",
        "76": "QT", "77": "QR", "78": "SL", "79": "SL", "80": "SI", "81": "SI", "82": "SI", "83": "SO", "84": "SO", "85": "SO", "86": "TB", "87": "TM", "88": "TM", "89": "TM", "90": "TL", "91": "VE", "92": "VE", "93": "VE", "94": "VE", "95": "VE", "96": "VE", "97": "YU", "98": "ZA", "99": "ZA"
    }
    return mapeo.get(prefijo, "")

# ==========================================
# MÓDULO: COTIZADOR (OPTIMIZADO)
# ==========================================

@st.cache_data(show_spinner="Cargando empaques de Envia...")
def obtener_paquetes_envia(token):
    try:
        url = "https://queries.envia.com/company-packages"
        headers = {"Authorization": f"Bearer {token}"}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, dict) and "data" in data:
                d = data["data"]
                if isinstance(d, dict):
                    user_pkg = d.get("userPackages", [])
                    comp_pkg = d.get("companyPackages", [])
                    # Garantizar que sean listas
                    if not isinstance(user_pkg, list):
                        user_pkg = []
                    if not isinstance(comp_pkg, list):
                        comp_pkg = []
                    return user_pkg + comp_pkg
                elif isinstance(d, list):
                    return d
            elif isinstance(data, list):
                return data
    except Exception as e:
        pass
    return []

@st.cache_data(show_spinner=False)
def obtener_detalles_por_cp(cp):
    if not cp or len(cp) < 5:
        return "", ""
    try:
        url = f"https://geocodes.envia.com/zipcode/MX/{cp}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0:
                item = data[0]
                city = item.get("locality", "")
                state_info = item.get("state", {})
                state = ""
                if isinstance(state_info, dict):
                    state = state_info.get("code", {}).get("2digit", "")
                return city, state
    except:
        pass
    return "", ""

def app_cotizador():
    st.title("🚚 Cotizador de Envíos")
    
    # Obtener token de Envia
    token = st.secrets.get("ENVIA_TOKEN", "")
    if token:
        token = token.replace("Bearer ", "").strip()
        
    # Inicializar lista de paquetes en session_state
    if "packages_list" not in st.session_state:
        st.session_state.packages_list = [{
            "id": 0,
            "weight": 1.0,
            "length": 20,
            "width": 20,
            "height": 20,
            "amount": 1,
            "description": "manual",
            "search_txt": ""
        }]
        st.session_state.next_package_id = 1

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Origen")
        cp_o = st.text_input("CP Origen", value="89364")
        ciudad_o, estado_o = obtener_detalles_por_cp(cp_o)
        if ciudad_o and estado_o:
            st.caption(f"📍 {ciudad_o}, {estado_o}")
        else:
            estado_o = obtener_estado_por_cp(cp_o) or "TM"
            ciudad_o = "Tampico" if cp_o == "89364" else "Ciudad Origen"
            st.caption(f"📍 {ciudad_o}, {estado_o} (localizado localmente)")

    with col2:
        st.subheader("Destino")
        cp_d = st.text_input("CP Destino", value="")
        ciudad_d, estado_d = obtener_detalles_por_cp(cp_d) if cp_d else ("", "")
        if ciudad_d and estado_d:
            st.caption(f"📍 {ciudad_d}, {estado_d}")
        else:
            estado_d = obtener_estado_por_cp(cp_d)
            ciudad_d = "Ciudad Destino"
            if cp_d:
                st.caption(f"📍 {ciudad_d}, {estado_d} (localizado localmente)")

    st.markdown("---")
    
    # Cargar empaques si hay token
    paquetes = []
    if token:
        paquetes = obtener_paquetes_envia(token)

    st.subheader("📦 Lista de Paquetes")
    
    # Renderizar cada paquete en la lista
    for idx in range(len(st.session_state.packages_list)):
        if idx >= len(st.session_state.packages_list):
            break
        pkg = st.session_state.packages_list[idx]
        
        # Asegurar que cada paquete tenga un ID único
        if "id" not in pkg:
            pkg["id"] = idx
            if st.session_state.get("next_package_id", 1) <= idx:
                st.session_state.next_package_id = idx + 1
                
        pkg_id = pkg["id"]
        
        st.write(f"**Caja #{idx + 1}**")
        
        # Filtro y selección alineados en la misma fila (lado a lado)
        col_search, col_select = st.columns([1, 2])
        with col_search:
            filtro_txt = st.text_input("🔍 Buscar SKU/Nombre:", key=f"filtro_{pkg_id}", value=pkg.get("search_txt", "")).strip().lower()
            pkg["search_txt"] = filtro_txt
            
        paquetes_filtrados = []
        if paquetes:
            for p in paquetes:
                nombre = p.get("description") or p.get("content") or p.get("name") or ""
                if not filtro_txt or filtro_txt in nombre.lower():
                    paquetes_filtrados.append(p)
                    
        opciones = ["Ingresar manualmente"]
        paquetes_dict = {}
        for p in paquetes_filtrados:
            nombre = p.get("description") or p.get("content") or p.get("name") or f"Paquete #{p.get('package_id', '')}"
            desc = f"📦 {nombre} ({p.get('length', 0)}x{p.get('width', 0)}x{p.get('height', 0)} cm - {p.get('weight', 0)} kg)"
            opciones.append(desc)
            paquetes_dict[desc] = p
            
        def get_default_index(i_id=pkg_id, ops=opciones):
            for o in ops:
                if o in paquetes_dict:
                    p = paquetes_dict[o]
                    pkg_current = next((x for x in st.session_state.packages_list if x.get("id") == i_id), None)
                    if pkg_current and (float(p.get("weight", 1.0)) == float(pkg_current["weight"]) and
                        int(float(p.get("length", 20))) == int(pkg_current["length"]) and
                        int(float(p.get("width", 20))) == int(pkg_current["width"]) and
                        int(float(p.get("height", 20))) == int(pkg_current["height"])):
                        return ops.index(o)
            return 0
            
        with col_select:
            def al_cambiar_paquete(i_id=pkg_id):
                sel = st.session_state[f"sel_paquete_{i_id}"]
                pkg_current = next((x for x in st.session_state.packages_list if x.get("id") == i_id), None)
                if pkg_current:
                    if sel in paquetes_dict:
                        pkg_sel = paquetes_dict[sel]
                        w_val = float(pkg_sel.get("weight", 1.0))
                        l_val = int(float(pkg_sel.get("length", 20)))
                        w_dim = int(float(pkg_sel.get("width", 20)))
                        h_val = int(float(pkg_sel.get("height", 20)))
                        
                        pkg_current["weight"] = w_val
                        pkg_current["length"] = l_val
                        pkg_current["width"] = w_dim
                        pkg_current["height"] = h_val
                        pkg_current["description"] = pkg_sel.get("description") or pkg_sel.get("content") or "box"
                        
                        # Actualizar los estados de los widgets de Streamlit en session_state
                        st.session_state[f"weight_{i_id}"] = w_val
                        st.session_state[f"length_{i_id}"] = l_val
                        st.session_state[f"width_{i_id}"] = w_dim
                        st.session_state[f"height_{i_id}"] = h_val
                    else:
                        pkg_current["description"] = "manual"
            
            st.selectbox("Seleccionar empaque:", opciones, index=get_default_index(), key=f"sel_paquete_{pkg_id}", on_change=al_cambiar_paquete)

        # Inputs de dimensiones, peso, cantidad y botón eliminar alineados
        c_qty, c_weight, c_l, c_w, c_h, c_del = st.columns([1.5, 1.5, 1.5, 1.5, 1.5, 1])
        with c_qty:
            pkg["amount"] = st.number_input("Cantidad", min_value=1, value=int(pkg["amount"]), key=f"amount_{pkg_id}")
        with c_weight:
            pkg["weight"] = st.number_input("Peso (kg)", min_value=0.1, value=float(pkg["weight"]), step=0.1, key=f"weight_{pkg_id}")
        with c_l:
            pkg["length"] = st.number_input("Largo (cm)", min_value=1, value=int(pkg["length"]), key=f"length_{pkg_id}")
        with c_w:
            pkg["width"] = st.number_input("Ancho (cm)", min_value=1, value=int(pkg["width"]), key=f"width_{pkg_id}")
        with c_h:
            pkg["height"] = st.number_input("Alto (cm)", min_value=1, value=int(pkg["height"]), key=f"height_{pkg_id}")
        with c_del:
            st.write(" ")
            st.write(" ")
            if len(st.session_state.packages_list) > 1:
                def eliminar_paquete(i_id=pkg_id):
                    st.session_state.packages_list = [x for x in st.session_state.packages_list if x.get("id") != i_id]
                st.button("🗑️", key=f"del_{pkg_id}", on_click=eliminar_paquete)
        
        st.markdown("---")
        
    def agregar_paquete():
        st.session_state.packages_list.append({
            "id": st.session_state.next_package_id,
            "weight": 1.0,
            "length": 20,
            "width": 20,
            "height": 20,
            "amount": 1,
            "description": "manual",
            "search_txt": ""
        })
        st.session_state.next_package_id += 1
    st.button("➕ Agregar paquete", on_click=agregar_paquete)
    
    st.markdown("---")

    if st.button("Cotizar Todas las Paqueterías"):
        if not token:
            st.error("Falta el token de Envia en st.secrets (ENVIA_TOKEN).")
            return
        if not cp_d:
            st.error("Completa el CP de destino.")
            return

        # Lista de paqueterías a consultar
        paqueterias = ["afimex", "paquetexpress", "estafeta", "tresguerras", "fedex"]
        resultados_totales = []
        progress = st.progress(0)
        status = st.empty()
        
        for i, carrier in enumerate(paqueterias):
            status.text(f"Consultando {carrier.capitalize()}...")
            try:
                url = "https://api.envia.com/ship/rate/"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                # Consolidar paquetes para paqueterías que no soportan MPS consolidado nativo (como Estafeta, Tresguerras, Afimex)
                # Solo consolidamos si el peso total es menor o igual a 30 kg (límite estándar de peso por paquete individual)
                total_weight = sum(float(pkg.get("weight", 1.0)) * int(pkg.get("amount", 1)) for pkg in st.session_state.packages_list)
                if carrier in ["estafeta", "tresguerras", "afimex"] and len(st.session_state.packages_list) > 1 and total_weight <= 30.0:
                    max_length = max(int(pkg.get("length", 20)) for pkg in st.session_state.packages_list)
                    max_width = max(int(pkg.get("width", 20)) for pkg in st.session_state.packages_list)
                    max_height = max(int(pkg.get("height", 20)) for pkg in st.session_state.packages_list)
                    
                    packages_payload = [{
                        "type": "box",
                        "content": "box",
                        "amount": 1,
                        "declaredValue": 0,
                        "weight": total_weight,
                        "weightUnit": "KG",
                        "lengthUnit": "CM",
                        "dimensions": {
                            "length": max_length,
                            "width": max_width,
                            "height": max_height
                        }
                    }]
                else:
                    packages_payload = [{
                        "type": "box", 
                        "content": "box", 
                        "amount": int(pkg["amount"]), 
                        "declaredValue": 0,
                        "weight": float(pkg["weight"]), 
                        "weightUnit": "KG", 
                        "lengthUnit": "CM",
                        "dimensions": {
                            "length": int(pkg["length"]), 
                            "width": int(pkg["width"]), 
                            "height": int(pkg["height"])
                        }
                    } for pkg in st.session_state.packages_list]

                payload = {
                    "origin": {
                        "name": st.secrets.get("ORIGIN_NAME", "ARIZONE"),
                        "company": st.secrets.get("ORIGIN_COMPANY", "ARIZONE"),
                        "email": st.secrets.get("ORIGIN_EMAIL", "v@a.mx"),
                        "phone": st.secrets.get("ORIGIN_PHONE", "8330000000"),
                        "street": st.secrets.get("ORIGIN_STREET", "AV"),
                        "number": st.secrets.get("ORIGIN_NUMBER", "1"),
                        "district": st.secrets.get("ORIGIN_DISTRICT", "CENTRO"),
                        "city": ciudad_o, "state": estado_o, "country": "MX", "postalCode": str(cp_o)
                    },
                    "destination": {
                        "name": "CLIENTE", "company": "C", "email": "c@t.com", "phone": "8110000000",
                        "street": "C", "number": "1", "district": "CENTRO",
                        "city": ciudad_d, "state": estado_d, "country": "MX", "postalCode": str(cp_d)
                    },
                    "packages": packages_payload,
                    "shipment": {"type": 1, "carrier": carrier},
                    "settings": {"currency": "MXN"}
                }
                
                res_raw = requests.post(url, json=payload, headers=headers)
                data = res_raw.json()
                
                if "data" in data and data["data"]:
                    for r in data["data"]:
                        resultados_totales.append({
                            'Paquetería': r.get('carrierDescription', carrier.capitalize()),
                            'Servicio': r.get('serviceDescription', 'N/A'),
                            'Entrega': r.get('deliveryEstimate', 'N/A'),
                            'Costo ($)': r.get('totalPrice', 0)
                        })
                else:
                    # Si no hay datos, mostramos por qué falló esta paquetería específica
                    if "error" in data:
                        st.warning(f"Aviso {carrier.capitalize()}: {data['error']['message']}")
            except Exception as e:
                st.error(f"Error técnico consultando {carrier}: {e}")
            
            progress.progress((i + 1) / len(paqueterias))
        
        status.empty()
        progress.empty()

        if resultados_totales:
            df_view = pd.DataFrame(resultados_totales)
            st.success("Comparativa de tarifas generada:")
            st.dataframe(df_view.sort_values('Costo ($)'), use_container_width=True)
        else:
            st.warning("No se encontraron rutas disponibles en ninguna paquetería para estos datos.")

# ==========================================
# MÓDULO: CALCULADORA DE COMISIONES
# ==========================================

def app_calculadora():
    st.title("💰 Calculadora de Comisiones de Pago")
    st.markdown("Calcula cuánto recibes neto después de comisiones fijas y meses sin intereses.")

    datos_procesadores = {
        "OPENPAY GENERAL": {"fija": 2.90, "porcentajes": {0: 3.36, 3: 8.93, 6: 12.41, 9: 15.89, 12: 19.37}},
        "MERCADOPAGO GENERAL": {"fija": 4.64, "porcentajes": {0: 3.70, 3: 9.14, 6: 12.62, 9: 16.68, 12: 18.65}},
        "ECARTPAY GENERAL": {"fija": 4.29, "porcentajes": {0: 3.36, 3: 8.31, 6: 11.83, 9: 13.22, 12: 18.44}},
        "ECART AMEX": {"fija": 4.29, "porcentajes": {0: 3.36, 3: 7.1340, 6: 10.6140, 9: 12.9340, 12: 15.2540}}
    }

    st.sidebar.markdown("---")
    st.sidebar.header("Configuración de Venta")
    monto = st.sidebar.number_input("Monto de la venta ($)", min_value=1.0, value=1000.0, step=100.0)
    meses = st.sidebar.selectbox("Plazo en meses", options=[0, 3, 6, 9, 12])

    resultados = []
    for nombre, datos in datos_procesadores.items():
        pct = datos["porcentajes"][meses]
        fija = datos["fija"]
        com_var = monto * (pct / 100)
        total_com = com_var + fija
        neto = monto - total_com
        resultados.append({
            "Procesador": nombre, "% Comisión": f"{pct}%",
            "Comisión Var.": round(com_var, 2), "Comisión Fija": fija,
            "Total Com.": round(total_com, 2), "Recibes Neto": round(neto, 2)
        })

    df_res = pd.DataFrame(resultados)
    mejor = df_res.loc[df_res['Recibes Neto'].idxmax()]

    st.subheader("Resultados")
    c1, c2 = st.columns([1, 1])
    with c1:
        st.metric("Mejor Opción", mejor['Procesador'])
    with c2:
        st.metric("Neto Máximo a Recibir", f"${mejor['Recibes Neto']:,.2f}")
    
    st.markdown("---")
    st.subheader("Tabla Comparativa")
    st.dataframe(df_res.style.highlight_max(axis=0, subset=['Recibes Neto'], color='#90EE90'), use_container_width=True)

# ==========================================
# MÓDULO: CATÁLOGOS
# ==========================================

class CatalogoLista(FPDF):
    def __init__(self, mostrar_precio=True):
        super().__init__()
        self.mostrar_precio = mostrar_precio
        try:
            self.add_font("ArialCustom", "B", FONT_BOLD_PATH)
            self.fuente_pdf = "ArialCustom"
        except: self.fuente_pdf = "Helvetica"

    def header(self):
        self.set_fill_color(227, 29, 43)
        self.polygon([(185, 0), (210, 0), (210, 25)], fill=True)
        self.set_font(self.fuente_pdf, 'B', 11); self.set_text_color(255, 255, 255)
        self.set_xy(198, 4); self.cell(10, 10, str(self.page_no()), align='C')
        self.set_text_color(50, 50, 50); self.set_font(self.fuente_pdf, 'B', 10); self.set_xy(10, 10)
        self.cell(0, 10, "CATALOGO PRODUCTOS 2026", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def añadir_producto(self, sku, nombre, url_img, precio="", almacen=""):
        if self.get_y() > 210: self.add_page()
        y_ini = self.get_y()
        try:
            res = requests.get(url_img, timeout=5)
            img = Image.open(BytesIO(res.content))
            if img.mode in ("RGBA", "P"): img = img.convert("RGB")
            self.image(img, x=10, y=y_ini + 5, w=85, h=60, keep_aspect_ratio=True)
        except: self.rect(10, y_ini + 5, 85, 60)
        
        cX = 105; self.set_xy(cX, y_ini + 6); self.set_font(self.fuente_pdf, 'B', 18); self.set_text_color(227, 29, 43)
        self.cell(0, 10, str(sku).upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_x(cX); self.set_font(self.fuente_pdf, 'B', 11); self.set_text_color(0,0,0)
        self.multi_cell(95, 5, str(nombre))
        
        if self.mostrar_precio and precio:
            self.ln(2); self.set_x(cX); self.set_font(self.fuente_pdf, 'B', 14); self.set_text_color(227, 29, 43)
            p_limpio = str(precio).replace('$', '').strip()
            self.cell(0, 8, f"$ {p_limpio}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_x(cX); self.set_font(self.fuente_pdf, 'B', 7); self.set_text_color(100,100,100)
        self.cell(0, 5, f"Stock: {almacen}")
        self.set_y(y_ini + 75); self.set_draw_color(227, 29, 43); self.line(10, self.get_y(), 200, self.get_y()); self.ln(8)

def generate_grid_flyer_social(df_chunk, mostrar_precio=True):
    W, H = 1080, 1080
    img = Image.new('RGB', (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try: 
        f_title = ImageFont.truetype(FONT_BOLD_PATH, 60); f_sku = ImageFont.truetype(FONT_BOLD_PATH, 18)
        f_price = ImageFont.truetype(FONT_BOLD_PATH, 22); f_name = ImageFont.truetype(FONT_BOLD_PATH, 13)
    except: 
        f_title = f_sku = f_price = f_name = ImageFont.load_default()
    
    draw.rectangle([210, 35, 870, 115], fill=(227, 29, 43))
    draw.text((540, 75), "PROMOCIONES ACTIVAS", fill="white", font=f_title, anchor="mm")
    
    POSS = [(185, 360), (540, 360), (895, 360), (185, 780), (540, 780), (895, 780)]
    for i, (_, row) in enumerate(df_chunk.iterrows()):
        if i >= 6: break
        px, py = POSS[i]; x0, y0 = px - 165, py - 200
        draw.rectangle([x0, y0, x0+330, y0+400], outline=(220, 220, 220), width=1)
        try:
            res = requests.get(row['IMAGEN'], timeout=5)
            p_img = Image.open(BytesIO(res.content)).convert("RGBA")
            p_img.thumbnail((280, 240)); img.paste(p_img, (px - p_img.width // 2, y0 + 30), p_img if p_img.mode == 'RGBA' else None)
        except: pass
        
        y_s = y0 + 400 - 85; t_x = x0 + 15
        if mostrar_precio:
            p_txt = f"$ {str(row.get('PRECIO 1', '0')).replace('$', '').strip()}"
            pw = draw.textlength(p_txt, font=f_price) + 16
            draw.rectangle([x0+15, y_s, x0+15+pw, y_s+48], fill=(227, 29, 43))
            draw.text((x0+15+pw/2, y_s+24), p_txt, fill="white", font=f_price, anchor="mm")
            t_x += pw + 12
        draw.text((t_x, y_s+2), str(row['Sku']), fill=(50,50,50), font=f_sku)
        n_w = textwrap.wrap(str(row['Nombre']).upper(), width=20); y_n = y_s + 24
        for line in n_w[:3]: draw.text((t_x, y_n), line, fill=(0,0,0), font=f_name); y_n += 16
    return img

def generar_flyer_individual(row):
    W, H = 1080, 1080
    img = Image.new('RGB', (W, H), color=(255, 255, 255)); draw = ImageDraw.Draw(img)
    try: f_sku = ImageFont.truetype(FONT_BOLD_PATH, 75); f_name = ImageFont.truetype(FONT_BOLD_PATH, 55)
    except: f_sku = f_name = ImageFont.load_default()
    draw.rectangle([40, 40, 1040, 170], fill=(218, 207, 184))
    draw.text((540, 105), str(row['Sku']).upper(), fill=(0,0,0), font=f_sku, anchor="mm")
    try:
        res = requests.get(row['IMAGEN'], timeout=10)
        p_img = Image.open(BytesIO(res.content)).convert("RGBA")
        ratio = min(960 / p_img.width, 600 / p_img.height)
        p_img = p_img.resize((int(p_img.width*ratio), int(p_img.height*ratio)), Image.Resampling.LANCZOS)
        img.paste(p_img, (W//2 - p_img.width//2, 480 - p_img.height//2), p_img if p_img.mode == 'RGBA' else None)
    except: pass
    draw.rectangle([40, 830, 1040, 1040], fill=(218, 207, 184))
    lines = textwrap.wrap(str(row['Nombre']).upper(), width=28)
    yt = 880
    for l in lines[:2]: draw.text((540, yt), l, fill=(0,0,0), font=f_name, anchor="mm"); yt += 80
    return img

def generar_pdf_3x3_original(df, imagen_fondo=None, mostrar_precio=True):
    output = BytesIO(); c = canvas.Canvas(output, pagesize=A4); width, height = A4
    f_reader = ImageReader(imagen_fondo) if imagen_fondo else None
    try: pdfmetrics.registerFont(TTFont('Arial-Bold', FONT_BOLD_PATH)); f_bold = "Arial-Bold"
    except: f_bold = "Helvetica-Bold"
    cols, rows, margin, padding = 3, 3, 1 * cm, 0.35 * cm
    cell_w, cell_h = (width - 2*margin)/cols, (height - 2*margin)/rows
    style_n = ParagraphStyle('N', fontSize=8, leading=9, textColor=colors.black, fontName=f_bold)
    for i, row in df.iterrows():
        idx = i % 9
        if idx == 0:
            if f_reader: c.drawImage(f_reader, 0, 0, width=width, height=height)
            else: c.setFillColor(colors.white); c.rect(0, 0, width, height, fill=1)
            c.setFillColor(colors.HexColor("#333333")); c.roundRect(0.8*cm, height-1.2*cm, 5.5*cm, 0.7*cm, 3, fill=1)
            c.setFillColor(colors.white); c.setFont(f_bold, 10); c.drawCentredString(3.55*cm, height-0.95*cm, "PRODUCTOS DISPONIBLES")
        col, fil = idx % cols, rows - 1 - (idx // cols)
        x_b, y_b = margin + (col * cell_w), margin + (fil * cell_h)
        c.setStrokeColor(colors.black); c.setLineWidth(0.4); c.setFillColor(colors.white); c.rect(x_b+3, y_b+3, cell_w-6, cell_h-6, fill=1, stroke=1)
        try:
            img = ImageReader(BytesIO(requests.get(row['IMAGEN']).content))
            c.drawImage(img, x_b+padding, y_b+padding+(cell_h*0.4), width=cell_w-(2*padding), height=cell_h*0.5, preserveAspectRatio=True, anchor='c')
        except: pass
        c.setFont(f_bold, 9); c.setFillColor(colors.black); c.drawString(x_b+padding, y_b+padding+(cell_h*0.35), str(row['Sku']))
        p = Paragraph(str(row['Nombre']), style_n); _, ph = p.wrap(cell_w-(2*padding), cell_h*0.3); p.drawOn(c, x_b+padding, y_b+padding+(cell_h*0.35)-ph-2)
        if mostrar_precio:
            pv = f"$ {str(row.get('PRECIO 1', '0')).replace('$','')}"; tw = c.stringWidth(pv, f_bold, 10)
            c.setFillColor(colors.red); c.roundRect(x_b+padding, y_b+padding+8, tw+8, 14, 2, fill=1)
            c.setFillColor(colors.white); c.drawString(x_b+padding+4, y_b+padding+11.5, pv)
        if (i+1) % 9 == 0: c.showPage()
    c.save(); return output.getvalue()

# ==========================================
# MÓDULO: GENERADOR DE LINKS DE PAGO
# ==========================================

def app_pagos():
    import base64
    from datetime import datetime

    # --- Leer credenciales desde secrets ---
    pub_key = st.secrets.get("ECARTPAY_PUBLIC_KEY", "")
    priv_key = st.secrets.get("ECARTPAY_PRIVATE_KEY", "")

    def obtener_jwt_token(es_sandbox):
        pub, priv = pub_key.strip(), priv_key.strip()
        combined = f"{pub}:{priv}"
        encoded = base64.b64encode(combined.encode('utf-8')).decode('utf-8')
        base_url = "https://sandbox.ecartpay.com" if es_sandbox else "https://ecartpay.com"
        headers = {'accept': 'application/json', 'authorization': f'Basic {encoded}'}
        try:
            response = requests.post(f"{base_url}/api/authorizations/token", headers=headers)
            return response.json().get("token") if response.status_code == 200 else None
        except:
            return None

    # --- Manejo de la lista de items en session_state ---
    if 'items_pago' not in st.session_state:
        st.session_state.items_pago = []

    st.title("💳 Generador de Links con Múltiples Ítems")

    if not pub_key or not priv_key:
        st.error("⚠️ Faltan las credenciales `ECARTPAY_PUBLIC_KEY` y/o `ECARTPAY_PRIVATE_KEY` en los secrets de la app.")
        st.stop()

    # Configurar modo sandbox internamente a través de secrets (Falso por defecto)
    modo_sandbox = st.secrets.get("ECARTPAY_SANDBOX", False)

    # Sidebar: opciones del módulo
    with st.sidebar:
        st.divider()
        if st.button("🗑️ Limpiar lista de productos"):
            st.session_state.items_pago = []

    # Datos Generales
    col_a, col_b = st.columns(2)
    with col_a:
        nombre_link = st.text_input("Nombre del Link / Referencia", value="Cotizacion Arizone")
        cliente = st.text_input("Nombre del Cliente", value="Cliente Arz")
    with col_b:
        moneda = st.selectbox("Moneda", ["MXN", "USD"])

    st.divider()

    # Sección para capturar items
    st.subheader("Añadir Productos")
    c1, c2, c3, c4 = st.columns([4, 1, 2, 1])
    with c1:
        in_name = st.text_input("Nombre del producto/servicio")
    with c2:
        in_qty = st.number_input("Cantidad", min_value=1, value=1)
    with c3:
        in_price = st.number_input("Precio Unitario", min_value=0.0, step=0.1)
    with c4:
        st.write(" ")
        if st.button("➕ Añadir"):
            if in_name and in_price > 0:
                st.session_state.items_pago.append({
                    "name": in_name,
                    "quantity": int(in_qty),
                    "price": float(in_price)
                })

    # Tabla de items
    if st.session_state.items_pago:
        st.write("### Resumen de la Orden")
        st.table(st.session_state.items_pago)
        total_acumulado = sum(i['quantity'] * i['price'] for i in st.session_state.items_pago)
        st.write(f"**Total a cobrar: {total_acumulado:,.2f} {moneda}**")

        msi_seleccionados = []
        if moneda == "MXN":
            st.write("---")
            st.subheader("📅 Configuración de Meses Sin Intereses (MSI)")
            ofrecer_msi = st.checkbox("Ofrecer Meses Sin Intereses para esta venta", value=False)
            if ofrecer_msi:
                c_msi1, c_msi2, c_msi3 = st.columns(3)
                with c_msi1:
                    msi_3 = st.checkbox("3 meses", value=True)
                with c_msi2:
                    msi_6 = st.checkbox("6 meses", value=True)
                with c_msi3:
                    msi_9 = st.checkbox("9 meses", value=True)
                
                if msi_3: msi_seleccionados.append(3)
                if msi_6: msi_seleccionados.append(6)
                if msi_9: msi_seleccionados.append(9)
            st.write("---")

        if st.button("🚀 Generar Link de Pago con estos Items"):
            jwt = obtener_jwt_token(modo_sandbox)
            if jwt:
                base_url = "https://sandbox.ecartpay.com" if modo_sandbox else "https://ecartpay.com"
                payload = {
                    "name": nombre_link,
                    "first_name": cliente,
                    "currency": moneda,
                    "start_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "quantity_uses": -1,
                    "items": st.session_state.items_pago,
                    "shipping_address": {
                        "first_name": cliente,
                        "last_name": "N/A",
                        "address1": "Calle Limite Sur 412",
                        "country": {"code": "MX", "name": "Mexico"},
                        "state": {"code": "TM"},
                        "city": "Tampico",
                        "postal_code": "89364",
                        "phone": "8330000000"
                    }
                }
                if msi_seleccionados:
                    payload["installments_information"] = [
                        {"quantity": int(m), "fixed_installments": False}
                        for m in msi_seleccionados
                    ]
                with st.spinner("Creando link de pago..."):
                    res = requests.post(
                        f"{base_url}/api/templates",
                        headers={'Authorization': jwt, 'Content-Type': 'application/json'},
                        json=payload
                    )
                    if res.status_code in [200, 201]:
                        data = res.json()
                        url_final = data.get("payment_link")
                        if url_final:
                            st.success("¡Link generado exitosamente!")
                            st.code(url_final)
                            st.link_button("Abrir Pantalla de Pago", url_final)
                    else:
                        st.error(f"Error {res.status_code}: {res.text}")
            else:
                st.error("No se pudo autenticar con EcartPay. Verifica las credenciales en secrets.")
    else:
        st.info("Agrega al menos un producto para generar el link.")


# ==========================================
# MÓDULO MODIFICADO: COTIZAR PRIMERO, SELECCIONAR Y EMITIR DESPUÉS
# ==========================================
def app_generar_guias():
    # --- PROTECCIÓN POR PIN (Evitar acceso no autorizado) ---
    pin_correcto = st.secrets.get("GUIAS_PIN", "1234").strip()
    if "guias_autorizado" not in st.session_state:
        st.session_state.guias_autorizado = False

    if not st.session_state.guias_autorizado:
        st.subheader("🔒 Acceso Restringido")
        pin_ingresado = st.text_input("Introduce el PIN de acceso para entrar a este módulo:", type="password", key="guias_pin_input")
        if st.button("🔑 Ingresar", key="guias_pin_btn"):
            if pin_ingresado.strip() == pin_correcto:
                st.session_state.guias_autorizado = True
                st.success("¡Acceso concedido!")
                st.rerun()
            else:
                st.error("PIN incorrecto. Intenta de nuevo.")
        return

    # Si está autorizado, se muestra el módulo con opción de bloquear
    col_title, col_lock = st.columns([4, 1])
    with col_title:
        st.title("🎫 Generación de Guías con Inteligencia Artificial")
    with col_lock:
        st.write(" ")
        if st.button("🔒 Bloquear Módulo"):
            st.session_state.guias_autorizado = False
            st.rerun()
            
    token = st.secrets.get("ENVIA_TOKEN", "").replace("Bearer ", "").strip()
    gemini_key = st.secrets.get("GEMINI_API_KEY", "").strip()
    
    if not token:
        st.error("Falta el token de Envia en st.secrets (ENVIA_TOKEN).")
        return

    # Inicializar estados para las tarifas encontradas
    if "tarifas_disponibles" not in st.session_state:
        st.session_state.tarifas_disponibles = []
    if "payload_respaldo" not in st.session_state:
        st.session_state.payload_respaldo = None

    # --- SECCIÓN DE ENTRADA INTELIGENTE (IA) ---
    st.markdown("### 🧠 Entrada Inteligente de Dirección")
    with st.expander("✨ Pegar dirección en texto plano (La IA rellenará el destino automáticamente)", expanded=True):
        texto_direccion = st.text_area("Pega aquí el bloque de texto que te mandó tu cliente (Ej: Nombre, Calle, CP todo junto):", 
                                       placeholder="Ej: Enviar a Juan Pérez, cel 8331234567, Calle Hidalgo 302 Col. Centro, Tampico, Tamaulipas, CP 89000.")
        if st.button("🪄 Procesar y Rellenar Campos", type="primary"):
            if not gemini_key:
                st.error("No has configurado la `GEMINI_API_KEY` en tus secrets.")
            elif not texto_direccion:
                st.warning("Por favor escribe o pega algún texto.")
            else:
                with st.spinner("La Inteligencia Artificial está ordenando los datos..."):
                    datos_ia = parsear_direccion_con_ia(texto_direccion, gemini_key)
                    if datos_ia:
                        st.session_state["dest_name"] = datos_ia.get("name", "")
                        st.session_state["dest_phone"] = datos_ia.get("phone", "")
                        st.session_state["dest_street"] = datos_ia.get("street", "")
                        st.session_state["dest_number"] = datos_ia.get("number", "")
                        st.session_state["dest_interior"] = datos_ia.get("interiorNumber", "")
                        st.session_state["dest_district"] = datos_ia.get("district", "")
                        st.session_state["dest_city"] = datos_ia.get("city", "")
                        st.session_state["dest_state"] = datos_ia.get("state", "")
                        st.session_state["dest_cp"] = datos_ia.get("zipCode", "")
                        st.session_state["dest_ref"] = datos_ia.get("reference", "")
                        st.success("¡Campos de Destino actualizados con éxito!")
                        st.rerun()

    st.markdown("---")

    # --- DISEÑO EN 3 COLUMNAS ---
    col_origen, col_destino, col_paquete = st.columns([1.1, 1.1, 1.2])

    with col_origen:
        st.subheader("Dirección de Origen")
        orig_name = st.text_input("Nombre completo *", value=st.secrets.get("ORIGIN_NAME", "Arizone Supply"), key="orig_name")
        orig_company = st.text_input("Empresa", value=st.secrets.get("ORIGIN_COMPANY", "Arizone Supply"), key="orig_company")
        orig_email = st.text_input("Email", value=st.secrets.get("ORIGIN_EMAIL", "hector.arizone@gmail.com"), key="orig_email")
        orig_phone = st.text_input("Teléfono *", value=st.secrets.get("ORIGIN_PHONE", "8333315287"), key="orig_phone")
        orig_country = st.selectbox("País *", ["Mexico"], key="orig_country")
        orig_street = st.text_input("Calle *", value=st.secrets.get("ORIGIN_STREET", "Calle Limite Sur"), key="orig_street")
        orig_number = st.text_input("Número", value=st.secrets.get("ORIGIN_NUMBER", "412"), key="orig_number")
        orig_cp = st.text_input("Código postal *", value="89364", key="orig_cp")
        
        c_o, e_o = obtener_detalles_por_cp(orig_cp)
        orig_district = st.text_input("Colonia", value="Jesús Elías Piña IV, V y VI", key="orig_district")
        orig_city = st.text_input("Ciudad *", value=c_o if c_o else "Tampico", key="orig_city")
        orig_state = st.text_input("Estado *", value=e_o if e_o else "TM", key="orig_state")
        orig_rfc = st.text_input("RFC", key="orig_rfc")
        orig_ref = st.text_input("Referencia de dirección", key="orig_ref")

    with col_destino:
        st.subheader("Dirección de Destino")
        dest_name = st.text_input("Nombre completo *", key="dest_name")
        dest_company = st.text_input("Empresa", key="dest_company")
        dest_email = st.text_input("Email", value="cliente@gmail.com", key="dest_email")
        dest_phone = st.text_input("Teléfono *", key="dest_phone")
        dest_country = st.selectbox("País *", ["Mexico"], key="dest_country")
        dest_street = st.text_input("Calle *", key="dest_street")
        dest_number = st.text_input("Número", key="dest_number")
        dest_cp = st.text_input("Código postal *", key="dest_cp")
        
        c_d, e_d = obtener_detalles_por_cp(dest_cp) if dest_cp else ("", "")
        dest_district = st.text_input("Colonia", value=st.session_state.get("dest_district", ""), key="dest_district")
        dest_city = st.text_input("Ciudad *", value=c_d if c_d else st.session_state.get("dest_city", ""), key="dest_city")
        dest_state = st.text_input("Estado *", value=e_d if e_d else st.session_state.get("dest_state", ""), key="dest_state")
        dest_rfc = st.text_input("RFC", key="dest_rfc")
        dest_ref = st.text_input("Referencia de dirección", value=st.session_state.get("dest_ref", ""), key="dest_ref")

    with col_paquete:
        st.subheader("Tipo de Envío y Paquete")
        tipo_envio = st.radio("Tipo de Envío", ["Caja", "Sobre", "Carga"], horizontal=True)
        
        paquetes = obtener_paquetes_envia(token)
        filtro_p = st.text_input("🔍 Buscar empaque guardado SKU:", key="guias_filtro_sku").strip().lower()
        
        paquetes_filtrados = []
        for p in paquetes:
            n = p.get("description") or p.get("content") or p.get("name") or ""
            if not filtro_p or filtro_p in n.lower():
                paquetes_filtrados.append(p)
                
        opciones_p = ["Manual"]
        paquetes_dict = {}
        for p in paquetes_filtrados:
            n = p.get("description") or p.get("content") or p.get("name") or f"Paquete #{p.get('package_id', '')}"
            d = f"📦 {n} ({p.get('length', 0)}x{p.get('width', 0)}x{p.get('height', 0)} cm - {p.get('weight', 0)} kg)"
            opciones_p.append(d)
            paquetes_dict[d] = p
            
        sel_p = st.selectbox("Paquetes guardados", opciones_p, key="guias_sel_p")
        
        v_w, v_l, v_wd, v_h, v_desc = 1.0, 20, 20, 20, "box"
        if sel_p in paquetes_dict:
            p_sel = paquetes_dict[sel_p]
            v_w = float(p_sel.get("weight", 1.0))
            v_l = int(float(p_sel.get("length", 20)))
            v_wd = int(float(p_sel.get("width", 20)))
            v_h = int(float(p_sel.get("height", 20)))
            v_desc = p_sel.get("description") or p_sel.get("content") or "box"

        p_desc = st.text_input("Contenido *", value=v_desc)
        p_weight = st.number_input("Peso (KG) *", min_value=0.1, value=v_w, step=0.1)
        p_len = st.number_input("Largo (CM) *", min_value=1, value=v_l)
        p_wid = st.number_input("Ancho (CM) *", min_value=1, value=v_wd)
        p_hei = st.number_input("Alto (CM) *", min_value=1, value=v_h)
        
        st.markdown("---")
        
        # --- PASO 1: BOTÓN SÓLO PARA COTIZAR ---
        if st.button("🔍 Cotizar Opciones Disponibles", type="primary", use_container_width=True):
            if not (dest_name and dest_street and dest_cp and dest_phone):
                st.error("Por favor completa los campos obligatorios del Destinatario (*).")
                return
                
            with st.spinner("Consultando tarifas en tiempo real..."):
                url_rate = "https://api.envia.com/ship/rate/"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                try:
                    tarifas_encontradas = []
                    ultimo_payload = None
                    # Realizamos la cotización por cada paquetería para cumplir con la obligatoriedad de la llave 'carrier' en Envia API
                    for carrier in ["afimex", "paquetexpress", "estafeta", "tresguerras", "fedex"]:
                        payload = {
                            "origin": {
                                "name": orig_name, "company": orig_company, "email": orig_email, 
                                "phone": limpiar_telefono_10_digitos(orig_phone),
                                "street": orig_street, "number": orig_number, "district": orig_district,
                                "city": orig_city, "state": orig_state, "country": "MX", "postalCode": str(orig_cp)
                            },
                            "destination": {
                                "name": dest_name, "company": dest_company, "email": dest_email, 
                                "phone": limpiar_telefono_10_digitos(dest_phone),
                                "street": dest_street, "number": dest_number, "district": dest_district,
                                "city": dest_city, "state": dest_state, "country": "MX", "postalCode": str(dest_cp)
                            },
                            "packages": [{
                                "type": "box", "content": "box", "amount": 1, "declaredValue": 0,
                                "weight": p_weight, "weightUnit": "KG", "lengthUnit": "CM",
                                "dimensions": {"length": p_len, "width": p_wid, "height": p_hei}
                            }],
                            "shipment": {"type": 1, "carrier": carrier},
                            "settings": {"currency": "MXN"}
                        }
                        ultimo_payload = payload
                        res = requests.post(url_rate, json=payload, headers=headers)
                        res_data = res.json()
                        if "data" in res_data and res_data["data"]:
                            for r in res_data["data"]:
                                tarifas_encontradas.append(r)
                                
                    if tarifas_encontradas:
                        st.session_state.tarifas_disponibles = sorted(tarifas_encontradas, key=lambda x: x.get('totalPrice', 99999))
                        st.session_state.payload_respaldo = ultimo_payload
                        st.success(f"¡Se encontraron {len(st.session_state.tarifas_disponibles)} opciones de envío!")
                    else:
                        st.session_state.tarifas_disponibles = []
                        st.error("No se encontró cobertura en ninguna paquetería.")
                except Exception as e:
                    st.error(f"Error de conexión al cotizar: {e}")

    # --- PASO 2: SELECCIÓN MANUAL Y GENERACIÓN FINALES ---
    if st.session_state.tarifas_disponibles and st.session_state.payload_respaldo:
        st.markdown("---")
        st.subheader("📊 Selecciona la paquetería de tu preferencia")
        
        opciones_select = []
        mapeo_tarifas = {}
        
        for t in st.session_state.tarifas_disponibles:
            texto_opcion = f"🚚 {t['carrierDescription']} ({t['serviceDescription']}) - Est. Entrega: {t['deliveryEstimate']} - ${t['totalPrice']} MXN"
            opciones_select.append(texto_opcion)
            mapeo_tarifas[texto_opcion] = t
            
        paqueteria_elegida = st.selectbox("Opciones encontradas (Ordenadas por menor costo):", opciones_select)
        
        if st.button("🎫 Confirmar y Generar Guía Ahora", type="secondary", use_container_width=True):
            tarifa_final = mapeo_tarifas[paqueteria_elegida]
            payload_envio = st.session_state.payload_respaldo
            
            payload_envio["shipment"]["carrier"] = tarifa_final["carrier"]
            payload_envio["shipment"]["service"] = tarifa_final["service"]
            
            # Asegurar parámetros de configuración de impresión requeridos por Envia al generar etiqueta
            if "settings" not in payload_envio or not payload_envio["settings"]:
                payload_envio["settings"] = {"currency": "MXN"}
            payload_envio["settings"]["printFormat"] = "PDF"
            payload_envio["settings"]["printSize"] = "PAPER_4X6"
            
            # Restaurar el contenido original p_desc para la etiqueta, a menos que sea Afimex
            content_value = "box" if tarifa_final["carrier"] == "afimex" else p_desc
            for pkg in payload_envio.get("packages", []):
                pkg["content"] = content_value
            
            with st.spinner(f"Emitiendo guía oficial con {tarifa_final['carrierDescription']}..."):
                url_gen = "https://api.envia.com/ship/generate/"
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                try:
                    res_gen = requests.post(url_gen, json=payload_envio, headers=headers)
                    gen_data = res_gen.json()
                    
                    if "data" in gen_data and gen_data["data"]:
                        info_guia = gen_data["data"][0]
                        st.success("🎉 ¡Guía Creada Exitosamente!")
                        st.write(f"**Número de Rastreo:** `{info_guia.get('trackingNumber')}`")
                        
                        url_pdf = info_guia.get("label")
                        if url_pdf:
                            st.link_button("📥 Descargar Guía (PDF)", url_pdf, type="primary")
                            
                        st.session_state.tarifas_disponibles = []
                        st.session_state.payload_respaldo = None
                    else:
                        st.error(f"Error de Envia al generar: {gen_data.get('error', {}).get('message', 'Desconocido')}")
                except Exception as e:
                    st.error(f"Error de conexión al emitir la guía: {e}")


# ==========================================
# NAVEGACIÓN Y CONTROL
# ==========================================

menu = st.sidebar.selectbox("Módulo:", ["Suite ARIZONE 2026", "Emitir Guías (IA)", "Calculadora de Comisiones", "Cotizador Envia", "Generador de Pagos"])

if menu == "Emitir Guías (IA)":
    app_generar_guias()
elif menu == "Calculadora de Comisiones":
    app_calculadora()
elif menu == "Cotizador Envia":
    app_cotizador()
elif menu == "Generador de Pagos":
    app_pagos()
else:
    st.sidebar.title("Herramientas ARIZONE")
    opc = st.sidebar.radio("Herramienta:", ["Inicio", "Flyer Individual (1080p)", "Volantes Grid (Redes)", "Catálogo Lista", "Catálogo 3x3 Pro"])
    mostrar_p = st.sidebar.checkbox("Mostrar PRECIO 1", value=True)
    
    if opc == "Inicio":
        st.title("Suite Arizone")
        st.success("Bienvenido. Usa el menú lateral para subir tu base de datos.")
    else:
        file = st.file_uploader("Sube Excel o CSV", type=['csv', 'xlsx'])
        bg = None
        if opc == "Catálogo 3x3 Pro":
            u = st.file_uploader("Fondo"); bg = BytesIO(u.read()) if u else None
        
        if file:
            try:
                df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                # Normalizar nombres de columnas
                df.columns = [str(c).strip() for c in df.columns]
                
                mapeo_columnas = {}
                for col in df.columns:
                    col_lower = col.lower()
                    if col_lower == 'sku':
                        mapeo_columnas[col] = 'Sku'
                    elif col_lower in ['nombre', 'name']:
                        mapeo_columnas[col] = 'Nombre'
                    elif col_lower in ['imagen', 'img', 'image']:
                        mapeo_columnas[col] = 'IMAGEN'
                    elif col_lower in ['precio 1', 'precio', 'price']:
                        mapeo_columnas[col] = 'PRECIO 1'
                    elif col_lower in ['almacen', 'stock', 'almacén']:
                        mapeo_columnas[col] = 'Almacen'
                
                df = df.rename(columns=mapeo_columnas)
                
                # Validar columnas requeridas
                columnas_requeridas = ['Sku', 'Nombre', 'IMAGEN']
                columnas_faltantes = [c for c in columnas_requeridas if c not in df.columns]
                
                if columnas_faltantes:
                    st.error(f"⚠️ El archivo no contiene las columnas necesarias: {', '.join(columnas_faltantes)}. Asegúrate de que las columnas tengan nombres similares a: Sku, Nombre, Imagen.")
                else:
                    st.success("✅ Archivo cargado y validado correctamente.")
                    st.write("Vista previa de los datos:")
                    st.dataframe(df.head(3), use_container_width=True)
                    
                    if st.button("Generar Todo"):
                        if opc == "Flyer Individual (1080p)":
                            zb = BytesIO()
                            with zipfile.ZipFile(zb, "a") as zf:
                                for i, r in df.iterrows():
                                    img = generar_flyer_individual(r)
                                    buf = BytesIO(); img.save(buf, format='PNG'); zf.writestr(f"flyer_{r.get('Sku',i)}.png", buf.getvalue())
                            st.download_button("Bajar Flyers", zb.getvalue(), "Flyers.zip")
                        elif opc == "Volantes Grid (Redes)":
                            zb = BytesIO()
                            with zipfile.ZipFile(zb, "a") as zf:
                                for i in range(0, len(df), 6):
                                    img = generate_grid_flyer_social(df.iloc[i:i+6], mostrar_p)
                                    buf = BytesIO(); img.save(buf, format='PNG'); zf.writestr(f"grid_{i//6+1}.png", buf.getvalue())
                            st.download_button("Bajar Grids", zb.getvalue(), "Grids.zip")
                        elif opc == "Catálogo Lista":
                            pdf = CatalogoLista(mostrar_precio=mostrar_p); pdf.add_page()
                            for _, r in df.iterrows(): pdf.añadir_producto(r['Sku'], r['Nombre'], r['IMAGEN'], r.get('PRECIO 1',''), r.get('Almacen',''))
                            st.download_button("Bajar Lista PDF", bytes(pdf.output()), "Lista.pdf")
                        elif opc == "Catálogo 3x3 Pro":
                            st.download_button("Bajar 3x3 PDF", generar_pdf_3x3_original(df, bg, mostrar_p), "3x3_Pro.pdf")
            except Exception as e:
                st.error(f"Error al procesar el archivo: {e}")