import streamlit as st
import pandas as pd
import requests
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

def app_cotizador():
    st.title("🚚 Cotizador de Envíos")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Origen")
        cp_o = st.text_input("CP Origen", value="89364")
        est_o_auto = obtener_estado_por_cp(cp_o)
        estado_o = st.text_input("Estado Origen", value=est_o_auto if est_o_auto else "TM").upper()
        ciudad_o = st.text_input("Ciudad Origen", value="Tampico")
        peso = st.number_input("Peso total (kg)", min_value=0.1, value=1.0, step=0.1)

    with col2:
        st.subheader("Destino")
        cp_d = st.text_input("CP Destino", value="")
        est_d_auto = obtener_estado_por_cp(cp_d)
        estado_d = st.text_input("Estado Destino", value=est_d_auto).upper()
        ciudad_d = st.text_input("Ciudad Destino", value="")
        st.write("")
        st.info("Servicio: Parcel (Paquetería)")

    st.markdown("---")
    st.subheader("📦 Dimensiones (cm)")
    c1, c2, c3 = st.columns(3)
    largo = c1.number_input("Largo", min_value=1, value=20)
    ancho = c2.number_input("Ancho", min_value=1, value=20)
    alto = c3.number_input("Alto", min_value=1, value=20)

    if st.button("Cotizar Todas las Paqueterías"):
        if not cp_d or not ciudad_d:
            st.error("Completa el CP y Ciudad de destino.")
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
                token = st.secrets["ENVIA_TOKEN"].replace("Bearer ", "").strip()
                headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                
                payload = {
                    "origin": {
                        "name": "ARIZONE", "company": "ARIZONE", "email": "v@a.mx", "phone": "8331",
                        "street": "AV", "number": "1", "district": "CENTRO",
                        "city": ciudad_o, "state": estado_o, "country": "MX", "postalCode": str(cp_o)
                    },
                    "destination": {
                        "name": "CLIENTE", "company": "C", "email": "c@t.com", "phone": "811",
                        "street": "C", "number": "1", "district": "CENTRO",
                        "city": ciudad_d, "state": estado_d, "country": "MX", "postalCode": str(cp_d)
                    },
                    "packages": [{
                        "type": "box", "content": "autopartes", "amount": 1, "declaredValue": 500,
                        "weight": float(peso), "weightUnit": "KG", "lengthUnit": "CM",
                        "dimensions": {"length": int(largo), "width": int(ancho), "height": int(alto)}
                    }],
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

    # Sidebar: opciones del módulo
    with st.sidebar:
        st.divider()
        modo_sandbox = st.checkbox("Modo Sandbox", value=True)
        if st.button("🗑️ Limpiar lista de productos"):
            st.session_state.items_pago = []

    # Datos Generales
    col_a, col_b = st.columns(2)
    with col_a:
        nombre_link = st.text_input("Nombre del Link / Referencia", value="Cotizacion Arizone")
        cliente = st.text_input("Nombre del Cliente", value="Hector Rivera")
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
# NAVEGACIÓN Y CONTROL
# ==========================================

menu = st.sidebar.selectbox("Módulo:", ["Suite ARIZONE 2026", "Calculadora de Comisiones", "Cotizador Envia", "Generador de Pagos"])

if menu == "Calculadora de Comisiones":
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
            df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
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
