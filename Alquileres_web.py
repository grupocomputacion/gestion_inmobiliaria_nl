import streamlit as st
import pandas as pd
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
import os
import io
from fpdf import FPDF
from sqlalchemy import create_engine, text

# ==============================================================================
# UTILIDADES
# ==============================================================================
def f_m(valor):
    try:
        return f"$ {int(float(valor or 0)):,}".replace(",", ".")
    except:
        return "$ 0"

def cl(texto):
    try:
        return int(str(texto).replace(".", "").replace("$", "").replace(" ", ""))
    except:
        return 0

# ==============================================================================
# CONEXIÓN — SQLAlchemy + Supabase (un solo engine cacheado)
# ==============================================================================
@st.cache_resource
def obtener_engine():
    c = st.secrets["database"]
    url = (f"postgresql+psycopg2://{c['user']}:{c['password']}"
           f"@{c['host']}:{c['port']}/{c['database']}?sslmode=require")
    return create_engine(url, pool_pre_ping=True, isolation_level="AUTOCOMMIT")

def db_query(query, params=(), commit=False):
    """
    SELECT  → devuelve DataFrame (o None si falla)
    INSERT  → devuelve id del nuevo registro  (RETURNING id automático)
    UPDATE/DELETE/DDL → devuelve True
    Parámetros: usar %s  (o ? — se convierte automáticamente)
    Alias: usar "comillas dobles" en SQL, NO [corchetes]
    """
    query = query.replace("?", "%s").replace("[", '"').replace("]", '"')
    engine = obtener_engine()
    try:
        with engine.connect() as conn:
            if commit:
                q_up = query.strip().upper()
                if q_up.startswith("INSERT") and "RETURNING" not in q_up:
                    query = query.rstrip().rstrip(";") + " RETURNING id"
                result = conn.execute(text(query), params if params else {})
                if "RETURNING" in query.upper():
                    row = result.fetchone()
                    return row[0] if row else None
                return True
            else:
                return pd.read_sql_query(text(query), conn,
                                         params=params if params else None)
    except Exception as e:
        if "already exists" not in str(e):
            st.error(f"⚠️ Error DB: {e}")
        return None

import os

# --- LOGICA DE BIENVENIDA CORREGIDA ---
if "bienvenida_aceptada" not in st.session_state:
    st.session_state["bienvenida_aceptada"] = False

if not st.session_state["bienvenida_aceptada"]:
    # Estilo para centrar verticalmente y estética
    st.markdown("""
        <style>
        .block-container {
            padding-top: 5rem;
        }
        </style>
    """, unsafe_allow_html=True)

    _, col_logo, _ = st.columns([1, 2, 1])
    
    with col_logo:
        # 1. Intentamos obtener la ruta absoluta del logo
        directorio_actual = os.path.dirname(__file__)
        # Asegurate de que el nombre sea EXACTO (mayúsculas/minúsculas importan en Linux/Cloud)
        # Probá con "logo.png", "Logo.png" o el nombre exacto que tenga tu archivo
        nombre_archivo_logo = "alquileres.jpg" 
        ruta_logo = os.path.join(directorio_actual, nombre_archivo_logo)
        
        if os.path.exists(ruta_logo):
            st.image(ruta_logo, use_container_width=True)
        else:
            # Si no lo encuentra, mostramos un título prolijo y un aviso técnico
            st.markdown(f"<h1 style='text-align: center; color: #1E88E5;'>NL PROPIEDADES</h1>", unsafe_allow_html=True)
            st.error(f"⚠️ No se encontró el archivo '{nombre_archivo_logo}' en la carpeta raíz.")
            st.info(f"Ruta buscada: {ruta_logo}")
        
        st.markdown("<h3 style='text-align: center;'>Gestión Inmobiliaria Integral</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("🚀 INGRESAR AL SISTEMA", use_container_width=True, type="primary"):
            st.session_state["bienvenida_aceptada"] = True
            st.rerun()
            
    st.stop()
# ==============================================================================
# TABLAS (idempotente — solo crea si no existen)
# ==============================================================================
def init_tablas():
    ddls = [
        """CREATE TABLE IF NOT EXISTS bloques (
            id SERIAL PRIMARY KEY, nombre TEXT, direccion TEXT,
            barrio TEXT, localidad TEXT)""",
        """CREATE TABLE IF NOT EXISTS inquilinos (
            id SERIAL PRIMARY KEY, nombre TEXT, dni TEXT, celular TEXT,
            procedencia TEXT, grupo TEXT, emergencia TEXT)""",
        # Buscá esta parte en tu función init_tablas()
        """CREATE TABLE IF NOT EXISTS inmuebles (
            id SERIAL PRIMARY KEY, 
            id_bloque INTEGER REFERENCES bloques(id), 
            tipo TEXT, 
            precio_alquiler NUMERIC, 
            costo_contrato NUMERIC, 
            deposito_base NUMERIC, 
            estado TEXT,
            paga_expensas BOOLEAN DEFAULT FALSE, 
            monto_expensa NUMERIC DEFAULT 0      
        )""",
        """CREATE TABLE IF NOT EXISTS contratos (
            id SERIAL PRIMARY KEY, id_inmueble INTEGER, id_inquilino INTEGER,
            fecha_inicio DATE, fecha_fin DATE, monto_alquiler BIGINT DEFAULT 0,
            activo INTEGER DEFAULT 1)""",
        """CREATE TABLE IF NOT EXISTS deudas (
            id SERIAL PRIMARY KEY, id_contrato INTEGER, concepto TEXT,
            monto_debe BIGINT DEFAULT 0, monto_pago BIGINT DEFAULT 0,
            pagado INTEGER DEFAULT 0, fecha_pago DATE)""",
        """CREATE TABLE IF NOT EXISTS desarrollos (
            id SERIAL PRIMARY KEY, nombre TEXT, ubicacion TEXT, localidad TEXT)""",
        """CREATE TABLE IF NOT EXISTS lotes (
            id SERIAL PRIMARY KEY, id_desarrollo INTEGER, nro_lote TEXT,
            manzana TEXT, metros_cuadrados REAL, frente REAL, fondo REAL,
            servicios TEXT, observaciones TEXT,
            precio_contado REAL, moneda_contado TEXT DEFAULT 'U$D',
            entrega_monto REAL, moneda_entrega TEXT DEFAULT 'PESOS',
            cuotas_monto REAL, moneda_cuotas TEXT DEFAULT 'U$D',
            cant_cuotas INTEGER, amojonamiento TEXT DEFAULT 'NO',
            costo_amojonamiento REAL DEFAULT 0,
            titular_cedente TEXT, estado TEXT DEFAULT 'Libre')""",
        """CREATE TABLE IF NOT EXISTS compradores (
            id SERIAL PRIMARY KEY, nombre TEXT, dni_cuit TEXT,
            celular TEXT, domicilio TEXT, email TEXT)""",
        """CREATE TABLE IF NOT EXISTS ventas_lotes (
            id SERIAL PRIMARY KEY, id_lote INTEGER, id_comprador INTEGER,
            fecha_venta DATE, monto_total_usd REAL, entrega_usd REAL,
            cantidad_cuotas INTEGER, monto_cuota_usd REAL)""",
        """CREATE TABLE IF NOT EXISTS cuotas_lotes (
            id SERIAL PRIMARY KEY, id_venta INTEGER, nro_cuota INTEGER,
            monto_usd REAL, fecha_vencimiento DATE, pagado INTEGER DEFAULT 0,
            monto_pagado_usd REAL, fecha_pago DATE)""",
    ]
    for ddl in ddls:
        db_query(ddl, commit=True)

init_tablas()

# ==============================================================================
# GENERADORES DE PDF
# ==============================================================================
class PDFRecibo(FPDF):
    def header(self):
        if os.path.exists("alquileres.jpg"):
            self.image("alquileres.jpg", 10, 8, 30)
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "NL PROPIEDADES", ln=True, align="C")
        self.ln(5)
        
def generar_pdf_contrato(datos_u, datos_i, f_inicio, m_alq, m_dep, m_con, uso):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("alquileres.jpg"):
        pdf.image("alquileres.jpg", 10, 8, 30)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "CONTRATO DE LOCACION TEMPORARIA", 0, 1, "C")
    pdf.ln(5)
    pdf.set_font("Arial", "", 10)
    hoy = date.today()
    meses_nom = ["enero","febrero","marzo","abril","mayo","junio",
                 "julio","agosto","septiembre","octubre","noviembre","diciembre"]
    nom_i  = str(datos_i.get("nombre", "S/D")).upper()
    dni_i  = str(datos_i.get("dni", "S/D"))
    dir_i  = str(datos_i.get("procedencia", datos_i.get("domicilio", "S/D")))
    dir_u  = str(datos_u.get("direccion", datos_u.get("nombre_edificio", "S/D")))
    tipo_u = str(datos_u.get("tipo", "Unidad"))
    texto = (
        f'Entre NL PROPIEDADES, CUIT 30-71884850-0, domicilio en Av. Velez Sarsfield 745, '
        f'Córdoba Capital ("EL LOCADOR") y {nom_i}, DNI {dni_i}, domicilio en {dir_i} ("EL LOCATARIO"):\n\n'
        f'1) OBJETO: Inmueble en {dir_u}. Unidad: {tipo_u}. Uso: {uso}.\n\n'
        f'2) PLAZO: Contrato de 3 meses desde el {f_inicio.strftime("%d/%m/%Y")}.\n\n'
        f'3) PRECIO: Alquiler mensual $ {f_m(cl(m_alq))}.\n\n'
        f'4) GARANTIA: $ {f_m(cl(m_dep))}. Se reintegra al finalizar sin daños. '
        f'Ante incumplimiento queda como resarcimiento.\n\n'
        f'5) GASTOS: A cargo del locatario.\n\n'
        f'6) PROHIBICIONES: No se permite subarrendamiento ni mascotas.\n\n'
        f'7) FIRMA: Costo administrativo $ {f_m(cl(m_con))}.\n\n'
        f'8) MORA: Ante mora, el locatario deberá desalojar en 15 días.\n\n'
        f'El locatario declara recibir el inmueble en buen estado y se compromete a devolverlo en iguales condiciones\n\n'
    )
    # Verificamos si la unidad paga expensas (paga_e y monto_e vienen por parámetro)
    if paga_e:
        monto_f = f_m(monto_e) # Formateamos el monto
        texto_expensas = f"El inmueble alquilado paga EXPENSAS, el valor mensual es de: {monto_f}."
        
        # Aquí usas el método de tu librería PDF para escribir la línea
        # Ejemplo si usas FPDF:
        pdf.set_font("Arial", 'B', 10)
        pdf.multi_cell(0, 10, texto_expensas)
        pdf.set_font("Arial", '', 10)
        f'En prueba de conformidad, se firman dos ejemplares de un mismo tener en la ciudad de Cordoba, {hoy.day} de {meses_nom[hoy.month-1]} de {hoy.year}.\n\n'
    else:
        f'En prueba de conformidad, se firman dos ejemplares de un mismo tener en la ciudad de Cordoba, {hoy.day} de {meses_nom[hoy.month-1]} de {hoy.year}.\n\n'
        
    pdf.multi_cell(0, 6, texto.encode("latin-1","replace").decode("latin-1"))
    pdf.ln(10)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(90, 5, "NL PROPIEDADES", 0, 0, "L")
    pdf.cell(90, 5, "EL LOCATARIO", 0, 1, "R")
    pdf.ln(5)
    pdf.set_font("Arial", "", 9)
    pdf.cell(90, 8, "Firma: __________________________", 0, 0, "L")
    pdf.cell(90, 8, "Firma: __________________________", 0, 1, "R")
    pdf.cell(90, 8, "DNI/CUIT: 30-71884850-0", 0, 0, "L")
    pdf.cell(90, 8, f"DNI: {dni_i}", 0, 1, "R")
    raw = pdf.output(dest="S")
    return raw.encode("latin-1") if isinstance(raw, str) else bytes(raw)

# ==============================================================================
# FUNCIÓN GENERAR PDF PROFESIONAL CON FPDF (MARCA DE AGUA Y FIRMA)
# ==============================================================================
def generar_pdf_recibo(inquilino, fecha, monto, detalles):
    class PDF(FPDF):
        def marca_agua(self):
            self.set_font('Arial', 'B', 50)
            self.set_text_color(240, 240, 240)
            with self.rotation(45, 74, 105):
                self.text(40, 115, "PAGADO")

    # Forzamos A5 y márgenes estrechos para ganar espacio
    pdf = PDF(orientation='P', unit='mm', format='A5')
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=False) # Evitamos que salte de página solo
    pdf.add_page()
    
    pdf.marca_agua()
    
    # 1. LOGO Y ENCABEZADO
    ruta_logo = "alquileres.jpg" 
    if os.path.exists(ruta_logo):
        pdf.image(ruta_logo, x=10, y=10, w=25)
    
    pdf.set_xy(40, 12)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(0, 5, "NL PROPIEDADES", ln=True)
    pdf.set_font("Arial", '', 8)
    pdf.set_x(40)
    pdf.cell(0, 4, "Inmobiliaria: NL PROPIEDADES | CUIT: 30-71884850-0", ln=True)
    
    pdf.ln(8)
    pdf.line(10, 30, 138, 30)
    
    # 2. TÍTULO Y FECHA
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(0, 8, "RECIBO DE PAGO", ln=True, align='C')
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, f"Fecha: {fecha.strftime('%d/%m/%Y')}", ln=True, align='R')
    pdf.ln(3)
    
    # 3. CUERPO
    pdf.set_font("Arial", '', 10)
    pdf.write(6, "Recibimos de: ")
    pdf.set_font("Arial", 'B', 10)
    pdf.write(6, f"{inquilino}\n")
    
    pdf.set_font("Arial", '', 10)
    pdf.ln(4)
    pdf.cell(0, 6, "En concepto de:", ln=True)
    
    pdf.set_font("Arial", '', 9)
    for det in detalles:
        det_safe = det.encode('latin-1', 'ignore').decode('latin-1')
        pdf.multi_cell(0, 5, f"- {det_safe}")
    
    pdf.ln(4)
    
    # 4. TOTAL RECIBIDO (Sin fondo gris para que se vea el PAGADO)
    pdf.set_font("Arial", 'B', 11)
    # Eliminamos el parámetro 'True' del final para quitar el relleno gris
    pdf.cell(0, 8, f"TOTAL RECIBIDO: {f_m(monto)}", ln=True, align='L')
    
    # 5. FIRMA (Ajuste de posición para que no salte de página)
    # Usamos coordenadas fijas bajas pero seguras para A5
    y_para_firma = 175 
    
    # IMPORTANTE: Verificación de archivo de firma
    # Intentamos varias rutas por si Streamlit lo busca distinto
    ruta_firma = "FIRMA_RECIBO.png"
    if not os.path.exists(ruta_firma):
        # Intento 2: ruta absoluta basada en el archivo actual
        ruta_firma = os.path.join(os.path.dirname(__file__), "FIRMA_RECIBO.jpg")

    if os.path.exists(ruta_firma):
        # Subimos un poco la imagen (y_para_firma - 15) para que pise la línea
        pdf.image(ruta_firma, x=54, y=y_para_firma - 18, w=40)
    
    pdf.set_y(y_para_firma)
    pdf.set_font("Arial", 'I', 8)
    pdf.cell(0, 4, "__________________________", ln=True, align='C')
    pdf.cell(0, 4, "Firma Autorizada - NL PROPIEDADES", ln=True, align='C')
    
    pdf_output = pdf.output(dest='S')
    return bytes(pdf_output) if isinstance(pdf_output, (bytes, bytearray)) else pdf_output.encode('latin-1')

# ==============================================================================
# CONFIGURACIÓN Y MENÚ
# ==============================================================================
st.set_page_config(page_title="NL GESTIÓN", layout="wide")
st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #FFFFFF !important; }
[data-testid="stSidebar"] .stRadio div label p { color: #1A1A1A !important; font-weight: 600 !important; }
.stButton>button { background-color:#D4AF37; color:#000; font-weight:bold;
                   border-radius:8px; border:none; width:100%; }
.stButton>button:hover { background-color:#B8952E; }
h1,h2,h3 { border-bottom: 2px solid #D4AF37; padding-bottom:8px; }
</style>""", unsafe_allow_html=True)

with st.sidebar:
    if os.path.exists("alquileres.jpg"):
        st.image("alquileres.jpg", use_container_width=True)
    st.title("NL GESTIÓN")
    menu = st.radio("MENÚ:", [
        "🏠 Inventario", "📝 Nuevo Contrato", "💰 Cobranzas",
        "📉 Morosos", "🏧 Caja", "⚙️ Carga", "🌳 Lotes"
    ])
    st.divider()
    st.caption("Conectado a Supabase Cloud ☁️")

# ==============================================================================
# 1. INVENTARIO (VERSIÓN FINAL - CON COLORES Y BLINDAJE)
# ==============================================================================
if menu == "🏠 Inventario":
    st.header("🏠 Inventario Global de Unidades")
    
    # --- 1. FILTROS ---
    c1, c2 = st.columns(2)
    df_bl = db_query("SELECT nombre FROM bloques ORDER BY nombre")
    lista_bl = ["Todos"] + (df_bl["nombre"].tolist() if df_bl is not None else [])
    sel_edif = c1.selectbox("Filtrar por Edificio", lista_bl)
    sel_disp = c2.selectbox("Filtrar por Estado", ["Todos", "Libre", "Ocupado"])

    # --- 2. CONSULTA DE DETALLE ---
    q = """
        SELECT 
            b.nombre AS "Inmueble", 
            i.tipo AS "Unidad",
            i.precio_alquiler AS "Alquiler",
            CASE WHEN c.id IS NOT NULL THEN 'Ocupado' ELSE 'Libre' END AS "Estado",
            CASE WHEN c.id IS NOT NULL THEN CAST(c.fecha_fin AS TEXT)
                 ELSE 'Disponible hoy' END AS "Disponible Desde"
        FROM inmuebles i
        LEFT JOIN bloques b ON i.id_bloque = b.id
        LEFT JOIN contratos c ON i.id = c.id_inmueble AND c.activo = 1
        WHERE 1=1
    """
    if sel_edif != "Todos":
        q += f" AND b.nombre = '{sel_edif}'"

    df_detalle = db_query(q)

    # --- 3. NORMALIZACIÓN Y LÓGICA DE COLORES ---
    if df_detalle is not None and not df_detalle.empty:
        # Normalizamos nombres de columnas para evitar KeyErrors
        df_detalle.columns = [c.strip() for c in df_detalle.columns]
        
        # Filtro de Estado (antes de poner los emojis para que el filtro funcione con texto limpio)
        if sel_disp != "Todos":
            df_detalle = df_detalle[df_detalle["Estado"] == sel_disp]

        # Métricas (Cálculo exacto)
        m1, m2, m3 = st.columns(3)
        total = len(df_detalle)
        ocupadas = len(df_detalle[df_detalle["Estado"] == "Ocupado"])
        
        m1.metric("Total Unidades", total)
        m2.metric("Ocupadas", ocupadas)
        m3.metric("Libres", total - ocupadas)

        # --- 4. PREPARACIÓN DE VISTA (INDICADORES VISUALES) ---
        st.write("### Detalle de Unidades")
        df_display = df_detalle.copy()
        
        # Aplicamos los círculos de color según el estado
        df_display["Estado"] = df_display["Estado"].apply(
            lambda x: f"🔴 {x}" if x == "Ocupado" else f"🟢 {x}"
        )
        
        # Formateamos moneda
        if "Alquiler" in df_display.columns:
            df_display["Alquiler"] = df_display["Alquiler"].apply(f_m)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
    else:
        st.info("ℹ️ No hay unidades para mostrar con los filtros seleccionados.")


# ==============================================================================
# 2. NUEVO CONTRATO (VERSION CORREGIDA)
# ==============================================================================
elif menu == "📝 Nuevo Contrato":
    st.header("📝 Formalización de Contrato")
    u_raw = db_query("SELECT i.*, b.nombre as nombre_bloque, b.direccion FROM inmuebles i LEFT JOIN bloques b ON i.id_bloque = b.id")
    i_raw = db_query("SELECT * FROM inquilinos")

    if u_raw is None or u_raw.empty:
        st.warning("No hay unidades cargadas. Vaya a ⚙️ Carga primero.")
        st.stop()
    if i_raw is None or i_raw.empty:
        st.warning("No hay inquilinos cargados. Vaya a ⚙️ Carga primero.")
        st.stop()

    c1, c2 = st.columns(2)
    # Limpieza preventiva de nombres de columnas
    u_raw.columns = [c.strip() for c in u_raw.columns]
    
    dict_u = {f"{r['nombre_bloque']} — {r['tipo']}": r["id"] for _, r in u_raw.iterrows()}
    u_sel  = c1.selectbox("Unidad", sorted(dict_u.keys()))
    uid    = dict_u[u_sel]

    dict_i = {r["nombre"]: r["id"] for _, r in i_raw.iterrows()}
    i_sel  = c2.selectbox("Inquilino", sorted(dict_i.keys()))
    iid    = dict_i[i_sel]

    s_u = u_raw[u_raw["id"] == uid].iloc[0]
    s_i = i_raw[i_raw["id"] == iid].iloc[0]

    with st.form("f_contrato"):
        st.subheader(f"Datos del contrato: {u_sel}")
        col1, col2 = st.columns(2)
        fini  = col1.date_input("Fecha Inicio", date.today())
        meses = col2.number_input("Duración (meses)", 1, 60, 6)
        uso_sel = st.radio("Destino:", ["Vivienda", "Comercial", "Vivienda / Comercial"], horizontal=True)
        
        v1, v2, v3 = st.columns(3)
        ma = v1.text_input("Alquiler $",  f_m(s_u.get("precio_alquiler", 0)))
        md = v2.text_input("Depósito $",  f_m(s_u.get("deposito_base", 0)))
        mc = v3.text_input("Gastos Cto $", f_m(s_u.get("costo_contrato", 0)))

        # --- INFO DE EXPENSAS (CORREGIDO) ---
        paga_e = bool(s_u.get("paga_expensas", False))
        monto_e = float(s_u.get("monto_expensa", 0))
        
        if paga_e:
            st.info(f"💡 Esta unidad paga Expensas: **{f_m(monto_e)}** (Se generará deuda inicial)")
        else:
            # CAMBIO: Usamos st.write en lugar de st.secondary que no existe
            st.write("ℹ️ *Esta unidad no registra cobro de expensas.*")

        # El botón de submit DEBE ejecutarse para que el formulario sea válido
        guardar = st.form_submit_button("✅ GUARDAR Y GENERAR CONTRATO PDF")

    if guardar:
        try:
            f_v  = fini + relativedelta(months=int(meses))
            # Insertar contrato con RETURNING para obtener el ID en Postgres
            nid  = db_query(
                """INSERT INTO contratos (id_inmueble, id_inquilino, fecha_inicio, fecha_fin, monto_alquiler, activo) 
                   VALUES (:id_u, :id_i, :f_ini, :f_fin, :monto, 1) RETURNING id""",
                {"id_u": int(uid), "id_i": int(iid), "f_ini": fini, "f_fin": f_v, "monto": cl(ma)}, commit=True)
            
            if nid:
                # 1. Deuda Alquiler
                db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, pagado) VALUES (:id, 'Alquiler', :monto, 0)", 
                         {"id": nid, "monto": cl(ma)}, commit=True)
                # 2. Deuda Depósito
                db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, pagado) VALUES (:id, 'Depósito', :monto, 0)", 
                         {"id": nid, "monto": cl(md)}, commit=True)
                
                # 3. DEUDA DE EXPENSAS
                if paga_e:
                    db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, pagado) VALUES (:id, 'Expensas', :monto, 0)", 
                             {"id": nid, "monto": monto_e}, commit=True)

                # Generación del PDF (Asegúrate que la función acepte estos 2 nuevos argumentos)
                pdf_bytes = generar_pdf_contrato(s_u.to_dict(), s_i.to_dict(), fini, ma, md, mc, uso_sel, paga_e, monto_e)
                
                st.session_state["pdf_f"] = pdf_bytes
                st.session_state["id_f"]  = nid
                st.success(f"✅ Contrato #{nid} registrado.")
                st.rerun()
            else:
                st.error("Error al obtener ID del contrato.")
        except Exception as e:
            st.error(f"Error al procesar contrato: {e}")

    # Bloque de descarga
    if st.session_state.get("pdf_f"):
        cid = st.session_state.get("id_f", "N/A")
        st.download_button(f"📥 Descargar Contrato #{cid}",
                           st.session_state["pdf_f"],
                           f"Contrato_{cid}.pdf", "application/pdf")
        if st.button("Limpiar"):
            del st.session_state["pdf_f"]
            st.rerun()



# ==============================================================================
# 3. COBRANZAS (VERSIÓN FINAL - FIX DICCIONARIOS)
# ==============================================================================
elif menu == "💰 Cobranzas":
    st.header("💰 Gestión de Cobranzas")

    if st.session_state.get("pago_exitoso"):
        st.success("✅ Pago registrado con éxito.")
        c_pdf, c_res = st.columns(2)
        if st.session_state.get("pdf_cobr"):
            c_pdf.download_button("📥 Descargar Recibo PDF",
                                  st.session_state["pdf_cobr"],
                                  st.session_state.get("nombre_pdf","Recibo.pdf"),
                                  "application/pdf", use_container_width=True)
        if c_res.button("🔄 Nueva Cobranza", use_container_width=True):
            for k in ["pago_exitoso","pdf_cobr","nombre_pdf"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.stop()

    deu_pend = db_query("""
        SELECT d.id AS "id_deuda", inq.nombre AS "Inquilino",
               b.nombre || ' - ' || i.tipo AS "Referencia",
               d.concepto AS "Concepto",
               (d.monto_debe - COALESCE(d.monto_pago,0)) AS "Saldo_Pendiente"
        FROM deudas d
        JOIN contratos c  ON d.id_contrato = c.id
        JOIN inmuebles i  ON c.id_inmueble  = i.id
        JOIN bloques b    ON i.id_bloque    = b.id
        JOIN inquilinos inq ON c.id_inquilino = inq.id
        WHERE d.pagado = 0 AND (d.monto_debe - COALESCE(d.monto_pago,0)) > 0
        ORDER BY inq.nombre
    """)

    if deu_pend is None or deu_pend.empty:
        st.success("✅ No hay deudas pendientes.")
        st.stop()

    deu_pend.columns = [c.strip() for c in deu_pend.columns]
    deu_pend = deu_pend.reset_index(drop=True)

    indices_sel = st.multiselect(
        "Seleccionar deudas a cobrar:",
        options=deu_pend.index.tolist(),
        format_func=lambda x: f"{deu_pend.loc[x, 'Inquilino']} | {deu_pend.loc[x, 'Concepto']} | ${float(deu_pend.loc[x, 'Saldo_Pendiente']):,.0f}"
    )

    total_marcado = float(deu_pend.loc[indices_sel, "Saldo_Pendiente"].sum()) if indices_sel else 0.0
    
    st.markdown(f"""
        <div style="background:#f0f2f6;padding:15px;border-radius:10px;border-left:5px solid #D4AF37;margin-bottom:12px;">
            <h3 style="margin:0;">TOTAL SELECCIONADO: <span style="color:#D4AF37;">$ {total_marcado:,.0f}</span></h3>
        </div>""", unsafe_allow_html=True)

    with st.form("f_cobro"):
        c1, c2 = st.columns(2)
        f_pago = c1.date_input("Fecha de cobro", date.today())
        m_r = c2.number_input("Monto recibido ($)", min_value=0.0, value=total_marcado, step=100.0, format="%.0f")
        btn = st.form_submit_button("✅ REGISTRAR Y GENERAR RECIBO", use_container_width=True)

    if btn:
        if not indices_sel:
            st.error("Seleccione al menos una deuda.")
        elif m_r <= 0:
            st.error("El monto debe ser mayor a cero.")
        else:
            try:
                saldo_a = m_r
                df_filas = deu_pend.loc[indices_sel].copy()
                detalles = []
                for _, fila in df_filas.iterrows():
                    if saldo_a <= 0: break
                    p = float(fila["Saldo_Pendiente"])
                    mp = p if saldo_a >= p else saldo_a
                    flag = 1 if saldo_a >= p else 0
                    
                    # --- CAMBIO CLAVE: Usamos Diccionario para evitar el error de argumento ---
                    db_query("""
                        UPDATE deudas 
                        SET monto_pago = COALESCE(monto_pago,0) + :mp, 
                            pagado = :flag, 
                            fecha_pago = :fecha 
                        WHERE id = :id_deuda
                    """, {
                        "mp": mp, 
                        "flag": flag, 
                        "fecha": f_pago.strftime("%Y-%m-%d"), 
                        "id_deuda": int(fila["id_deuda"])
                    }, commit=True)
                    
                    saldo_a -= mp
                    # --- REEMPLAZO EN EL BUCLE DE COBRANZAS ---
                    # Cambiamos el separador "—" por " - " que es 100% compatible
                    detalles.append(f"{fila['Concepto']} - {fila['Referencia']}: ${mp:,.0f} ({'Cancelado' if flag else 'Parcial'})")
                pdf_bytes = generar_pdf_recibo(df_filas.iloc[0]["Inquilino"], f_pago, m_r, detalles)
                st.session_state["pdf_cobr"] = pdf_bytes
                st.session_state["nombre_pdf"] = f"Recibo_{str(df_filas.iloc[0]['Inquilino']).replace(' ','_')}_{f_pago.strftime('%Y%m%d')}.pdf"
                st.session_state["pago_exitoso"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Error al registrar: {e}")
                
# ==============================================================================
# 4. MOROSOS (VERSIÓN CORREGIDA SENIOR)
# ==============================================================================
elif menu == "📉 Morosos":
    st.header("📉 Estado de Morosidad")
    
    # --- 1. CONSULTA CON ALIAS EXPLÍCITOS ---
    # Forzamos los nombres con comillas dobles para que Postgres no los pase a minúsculas
    df = db_query("""
        SELECT 
            inq.nombre AS "Inquilino",
            SUM(d.monto_debe - COALESCE(d.monto_pago,0)) AS "Deuda"
        FROM deudas d
        JOIN contratos c ON d.id_contrato = c.id
        JOIN inquilinos inq ON c.id_inquilino = inq.id
        WHERE d.pagado = 0
        GROUP BY inq.nombre 
        HAVING SUM(d.monto_debe - COALESCE(d.monto_pago,0)) > 0
        ORDER BY "Deuda" DESC
    """)

    # --- 2. VALIDACIÓN Y NORMALIZACIÓN ---
    if df is not None and not df.empty:
        # Limpieza preventiva de nombres de columnas
        df.columns = [c.strip() for c in df.columns]
        
        # Calculamos el total numérico antes de formatear la tabla para la vista
        total_deuda = float(df["Deuda"].sum())
        
        # --- 3. PREPARACIÓN DE VISTA ---
        df_v = df.copy()
        
        # Aplicamos formato moneda de forma segura
        if "Deuda" in df_v.columns:
            df_v["Deuda"] = df_v["Deuda"].apply(f_m)
            
        st.dataframe(df_v, use_container_width=True, hide_index=True)
        
        st.divider()
        
        # --- 4. MÉTRICAS DE CIERRE ---
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("### TOTAL DEUDA EN CALLE:")
        with c2:
            # Usamos un color de alerta para el total de deuda
            st.markdown(f"<h2 style='color: #E74C3C; margin:0;'>{f_m(total_deuda)}</h2>", unsafe_allow_html=True)
            
    else:
        st.success("✅ No hay deudas pendientes en el sistema.")

# ==============================================================================
# 5. CAJA (VERSIÓN FINAL ARREGLADA - SIN :: NI %S)
# ==============================================================================
elif menu == "🏧 Caja":
    st.header("🏧 Control de Caja")
    filtro = st.radio("Período:", ["Hoy", "Este Mes", "Este Año", "Total Histórico"], horizontal=True)
    hoy = date.today()
    
    # --- 1. CONFIGURACIÓN DE FILTROS (Uso de Diccionarios para SQLAlchemy) ---
    if filtro == "Hoy":
        # Usamos CAST en lugar de :: para no confundir a SQLAlchemy
        cond = "CAST(d.fecha_pago AS DATE) = :hoy"
        params = {"hoy": hoy.strftime("%Y-%m-%d")}
    elif filtro == "Este Mes":
        cond = "TO_CHAR(d.fecha_pago,'MM')=:mes AND TO_CHAR(d.fecha_pago,'YYYY')=:anio"
        params = {"mes": hoy.strftime("%m"), "anio": hoy.strftime("%Y")}
    elif filtro == "Este Año":
        cond = "TO_CHAR(d.fecha_pago,'YYYY')=:anio"
        params = {"anio": hoy.strftime("%Y")}
    else:
        cond = "1=1"
        params = {}

    # --- 2. CONSULTA CON ALIAS Y PARÁMETROS NOMBRADOS ---
    query_caja = f"""
        SELECT 
            d.id AS "ID_Reg", 
            inq.nombre AS "Inquilino",
            b.nombre || ' - ' || i.tipo AS "Unidad", 
            d.conceptO AS "Concepto",
            COALESCE(d.monto_pago,0) AS "Importe", 
            d.fecha_pago AS "Fecha"
        FROM deudas d
        JOIN contratos c ON d.id_contrato = c.id
        JOIN inmuebles i ON c.id_inmueble = i.id
        JOIN bloques b ON i.id_bloque = b.id
        JOIN inquilinos inq ON c.id_inquilino = inq.id
        WHERE COALESCE(d.monto_pago,0) > 0 
          AND d.fecha_pago IS NOT NULL 
          AND {cond}
        ORDER BY d.fecha_pago DESC
    """
    
    # Ejecutamos con el diccionario de parámetros
    df = db_query(query_caja, params)

    # --- 3. VALIDACIÓN Y VISUALIZACIÓN ---
    if df is not None and not df.empty:
        # Normalización total de columnas
        df.columns = [c.strip() for c in df.columns]
        
        # Calculamos el total de forma segura
        total_rec = float(df["Importe"].sum())
        
        # --- MÉTRICAS Y EXPORTACIÓN ---
        m1, m2 = st.columns([2, 1])
        m1.metric(f"Total Recaudado ({filtro})", f_m(total_rec))
        
        # Exportación Excel
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
            df.to_excel(w, sheet_name="Caja", index=False)
        
        m2.download_button("📥 Exportar Excel", buf.getvalue(),
                           f"Caja_{filtro}_{hoy}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
        
        # --- TABLA DE DATOS ---
        df_v = df.copy()
        if "Importe" in df_v.columns:
            df_v["Importe"] = df_v["Importe"].apply(f_m)
        
        # Mostramos ocultando el ID técnico
        cols_display = [c for c in df_v.columns if c != "ID_Reg"]
        st.dataframe(df_v[cols_display], use_container_width=True, hide_index=True)

        # --- 4. FUNCIONALIDAD DE ANULACIÓN (Blindada) ---
        st.divider()
        with st.expander("🛠️ Anular Pago"):
            id_an = st.selectbox(
                "Seleccione registro a anular", 
                df["ID_Reg"].tolist(),
                format_func=lambda x: f"ID: {x} - {df[df['ID_Reg']==x]['Inquilino'].values[0]} ({df[df['ID_Reg']==x]['Concepto'].values[0]})"
            )
            
            if st.button("❌ CONFIRMAR ANULACIÓN", use_container_width=True):
                # Usamos parámetros nombrados también aquí
                db_query("""
                    UPDATE deudas 
                    SET pagado=0, monto_pago=0, fecha_pago=NULL 
                    WHERE id=:id_an
                """, {"id_an": int(id_an)}, commit=True)
                st.success(f"✅ El pago ID {id_an} ha sido anulado.")
                st.rerun()
    else:
        st.info(f"ℹ️ No hay movimientos registrados para: {filtro}")


# ==============================================================================
# 6. CARGA (ABM completo)
# ==============================================================================
elif menu == "⚙️ Carga":
    st.header("⚙️ Administración de Base de Datos")
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "🏢 Inmuebles", "🏠 Unidades", "👤 Inquilinos",
        "📋 Contratos", "💾 Backup", "📋 Alquilados", "⚙️ Generación Mensual"
    ])

    # --- TAB 1: INMUEBLES (bloques) ---
    with t1:
        st.subheader("Edificios y Complejos")
        df_inm = db_query("SELECT id, nombre, direccion, barrio, localidad FROM bloques ORDER BY nombre")
        with st.expander("➕ Nuevo Inmueble"):
            with st.form("f_inm_alta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n = c1.text_input("Nombre"); d = c1.text_input("Dirección")
                b = c2.text_input("Barrio");  l = c2.text_input("Localidad")
                if st.form_submit_button("Guardar"):
                    db_query("INSERT INTO bloques (nombre,direccion,barrio,localidad) VALUES (%s,%s,%s,%s)",
                             (n,d,b,l), commit=True)
                    st.rerun()
        if df_inm is not None and not df_inm.empty:
            st.dataframe(df_inm.drop(columns=["id"]), use_container_width=True, hide_index=True)
            st.divider()
            sel = st.selectbox("Gestionar", df_inm["nombre"].tolist(), key="sel_inm")
            row = df_inm[df_inm["nombre"] == sel].iloc[0]
            with st.form("f_inm_edit"):
                c1, c2 = st.columns(2)
                en_n = c1.text_input("Nombre",    row["nombre"])
                en_d = c1.text_input("Dirección", row["direccion"])
                en_b = c2.text_input("Barrio",    row["barrio"])
                en_l = c2.text_input("Localidad", row["localidad"])
                cb1, cb2 = st.columns(2)
                if cb1.form_submit_button("💾 Actualizar"):
                    db_query("UPDATE bloques SET nombre=%s,direccion=%s,barrio=%s,localidad=%s WHERE id=%s",
                             (en_n,en_d,en_b,en_l,int(row["id"])), commit=True); st.rerun()
                if cb2.form_submit_button("🗑️ Eliminar"):
                    db_query("DELETE FROM bloques WHERE id=%s", (int(row["id"]),), commit=True); st.rerun()


    # --- TAB 2: UNIDADES ---
    with t2:
        st.subheader("🏢 Gestión de Unidades")

        # --- 1. ALTA DE NUEVA UNIDAD (REACTIVA) ---
        with st.expander("➕ Dar de Alta Nueva Unidad"):
            # Lógica reactiva para el Alta
            c_exp1, c_exp2 = st.columns(2)
            f_paga_exp = c_exp1.checkbox("¿Paga Expensas?", value=False, key="alta_paga")
            f_monto_exp = c_exp2.number_input("Monto Expensa Actual ($)", value=0, 
                                             disabled=not f_paga_exp, key="alta_monto")
            
            with st.form("form_alta_u"):
                df_bl = db_query("SELECT id, nombre FROM bloques ORDER BY nombre")
                if df_bl is not None and not df_bl.empty:
                    dic_bl = dict(zip(df_bl['nombre'], df_bl['id']))
                    f_bl = st.selectbox("Seleccione Edificio/Bloque", list(dic_bl.keys()))
                    f_tipo = st.text_input("Nombre/Descripción de Unidad (Ej: Dpto 1A)")
                    
                    c1, c2, c3 = st.columns(3)
                    f_alq = c1.number_input("Alquiler Base ($)", value=0)
                    f_con = c2.number_input("Costo Contrato ($)", value=0)
                    f_dep = c3.number_input("Depósito Base ($)", value=0)
                    
                    if st.form_submit_button("💾 Guardar Nueva Unidad"):
                        if f_tipo:
                            db_query("""
                                INSERT INTO inmuebles (id_bloque, tipo, precio_alquiler, costo_contrato, 
                                                     deposito_base, estado, paga_expensas, monto_expensa)
                                VALUES (:id_b, :tipo, :alq, :con, :dep, 'Libre', :paga, :monto)
                            """, {
                                "id_b": dic_bl[f_bl], "tipo": f_tipo, "alq": f_alq, 
                                "con": f_con, "dep": f_dep, "paga": f_paga_exp, "monto": f_monto_exp
                            }, commit=True)
                            st.success(f"✅ Unidad '{f_tipo}' creada con éxito.")
                            st.rerun()
                        else:
                            st.error("Debe ingresar un nombre para la unidad.")
                else:
                    st.warning("⚠️ Primero debe cargar un Edificio en la pestaña 'Inmuebles'.")

        st.divider()

        # --- 2. LISTA Y EDICIÓN DE UNIDADES EXISTENTES ---
        st.write("### Lista de Unidades y Edición")
        
        df_uni = db_query("""
            SELECT 
                i.id AS "id", 
                b.nombre AS "Inmueble", 
                i.tipo AS "Unidad",
                i.precio_alquiler AS "Alquiler", 
                i.costo_contrato AS "Contrato",
                i.deposito_base AS "Deposito", 
                i.estado AS "Estado",
                COALESCE(i.paga_expensas, false) AS "Paga_Exp",
                COALESCE(i.monto_expensa, 0) AS "Monto_Exp"
            FROM inmuebles i
            LEFT JOIN bloques b ON i.id_bloque = b.id
            ORDER BY b.nombre, i.tipo
        """)

        # VALIDACIÓN CRÍTICA
        if df_uni is None or df_uni.empty:
            st.info("ℹ️ No hay unidades cargadas. Use el formulario de arriba para dar de alta la primera.")
        else:
            df_uni.columns = [c.strip() for c in df_uni.columns]
            
            sel_idx = st.selectbox(
                "Seleccione una unidad para modificar o eliminar:", 
                options=df_uni.index.tolist(),
                format_func=lambda x: f"{df_uni.loc[x,'Inmueble']} - {df_uni.loc[x,'Unidad']} ({df_uni.loc[x,'Estado']})"
            )
            
            row_u = df_uni.loc[sel_idx]
            
            st.write(f"✍️ Editando: **{row_u['Inmueble']} - {row_u['Unidad']}**")
            
            # --- Lógica de Expensas FUERA del form ---
            ce1, ce2 = st.columns(2)
            e_paga_exp = ce1.checkbox("¿Paga Expensas?", value=bool(row_u["Paga_Exp"]), key=f"edit_paga_{row_u['id']}")
            e_monto_exp = ce2.number_input("Monto Expensa Actual ($)", 
                                             value=int(row_u["Monto_Exp"]), 
                                             disabled=not e_paga_exp,
                                             key=f"edit_monto_{row_u['id']}")

            with st.form(f"form_edit_{row_u['id']}"):
                e_tipo = st.text_input("Nombre de Unidad", value=str(row_u["Unidad"]))
                
                c1, c2, c3 = st.columns(3)
                e_alq = c1.number_input("Alquiler", value=int(row_u["Alquiler"]))
                e_con = c2.number_input("Contrato", value=int(row_u["Contrato"]))
                e_dep = c3.number_input("Depósito", value=int(row_u["Deposito"]))
                
                est_list = ["Libre", "Ocupado", "Reservado"]
                idx_est = est_list.index(row_u["Estado"]) if row_u["Estado"] in est_list else 0
                e_est = st.selectbox("Estado", est_list, index=idx_est)
                
                btn_c1, btn_c2 = st.columns(2)
                if btn_c1.form_submit_button("💾 Guardar Cambios"):
                    db_query("""
                        UPDATE inmuebles 
                        SET tipo = :tipo, precio_alquiler = :alq, costo_contrato = :con, 
                            deposito_base = :dep, estado = :est, paga_expensas = :paga, monto_expensa = :monto
                        WHERE id = :id
                    """, {
                        "tipo": e_tipo, "alq": e_alq, "con": e_con, "dep": e_dep, 
                        "est": e_est, "paga": e_paga_exp, "monto": e_monto_exp, "id": int(row_u["id"])
                    }, commit=True)
                    st.success("✅ Cambios actualizados.")
                    st.rerun()
                    
                if btn_c2.form_submit_button("🗑️ Eliminar Unidad"):
                    db_query("DELETE FROM inmuebles WHERE id = :id", {"id": int(row_u["id"])}, commit=True)
                    st.warning("🗑️ Unidad eliminada.")
                    st.rerun()


    # --- TAB 3: INQUILINOS ---
    with t3:
        st.subheader("Registro de Inquilinos")
        df_inq = db_query("SELECT id, nombre, dni, celular, procedencia, grupo, emergencia FROM inquilinos ORDER BY nombre")
        with st.expander("➕ Nuevo Inquilino"):
            with st.form("f_inq_alta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n   = c1.text_input("Nombre y Apellido"); dni = c1.text_input("DNI / CUIT")
                cel = c1.text_input("WhatsApp");          dom = c2.text_input("Domicilio")
                gru = c2.text_input("Grupo");             eme = c2.text_input("Emergencia")
                if st.form_submit_button("Guardar"):
                    db_query("INSERT INTO inquilinos (nombre,dni,celular,procedencia,grupo,emergencia) VALUES (%s,%s,%s,%s,%s,%s)",
                             (n,dni,cel,dom,gru,eme), commit=True); st.rerun()
        if df_inq is not None and not df_inq.empty:
            st.dataframe(df_inq.rename(columns={"procedencia":"Domicilio"}).drop(columns=["id"]),
                         use_container_width=True, hide_index=True)
            st.divider()
            sel_i = st.selectbox("Gestionar", df_inq["nombre"].tolist(), key="sel_inq")
            row_i = df_inq[df_inq["nombre"] == sel_i].iloc[0]
            with st.form("f_inq_edit"):
                c1, c2 = st.columns(2)
                en_n = c1.text_input("Nombre",    row_i["nombre"])
                en_d = c1.text_input("DNI",       row_i["dni"])
                en_c = c1.text_input("WhatsApp",  row_i["celular"])
                en_p = c2.text_input("Domicilio", row_i["procedencia"])
                en_g = c2.text_input("Grupo",     row_i["grupo"])
                en_e = c2.text_input("Emergencia",row_i["emergencia"])
                ci1, ci2 = st.columns(2)
                if ci1.form_submit_button("💾 Actualizar"):
                    db_query("UPDATE inquilinos SET nombre=%s,dni=%s,celular=%s,procedencia=%s,grupo=%s,emergencia=%s WHERE id=%s",
                             (en_n,en_d,en_c,en_p,en_g,en_e,int(row_i["id"])), commit=True); st.rerun()
                if ci2.form_submit_button("🗑️ Eliminar"):
                    db_query("DELETE FROM inquilinos WHERE id=%s", (int(row_i["id"]),), commit=True); st.rerun()

    # --- TAB 4: CONTRATOS ---
    with t4:
        st.subheader("Gestión de Contratos Vigentes")
        # --- 1. CONSULTA DE CONTRATOS CON ALIAS NORMALIZADOS ---
        q_cont = """
            SELECT 
                c.id as "ID_Contrato", 
                b.nombre as "Inmueble", 
                i.tipo as "Unidad", 
                iq.nombre as "Inquilino", 
                c.fecha_inicio as "Inicio", 
                c.fecha_fin as "Fin", 
                c.monto_alquiler as "Alquiler"
            FROM contratos c
            LEFT JOIN inmuebles i ON c.id_inmueble = i.id
            LEFT JOIN bloques b ON i.id_bloque = b.id
            LEFT JOIN inquilinos iq ON c.id_inquilino = iq.id
            ORDER BY c.id DESC
        """

        df_cont = db_query(q_cont)

        # --- 2. VISUALIZACIÓN PROTEGIDA (Línea 691) ---
        # --- REEMPLAZO PARA LÍNEA 967 (Sección de Contratos / Backup) ---

        df_cont = db_query("SELECT id AS \"ID_Contrato\", id_inquilino FROM contratos")

        # 1. VALIDACIÓN DE SEGURIDAD: Si no hay contratos, no seguimos.
        if df_cont is None or df_cont.empty:
            st.info("ℹ️ No hay contratos registrados en el sistema.")
        else:
            # 2. Solo si hay datos, armamos el selector
            lista_ids = df_cont["ID_Contrato"].tolist()
            sel_cid = st.selectbox("Seleccione ID de Contrato", lista_ids, key="sb_backup_cont")
            
            # 3. Filtramos
            df_filtrado = df_cont[df_cont["ID_Contrato"] == sel_cid]
            
            # 4. LA LÍNEA 967 PROTEGIDA: Solo pedimos iloc[0] si el filtro tiene algo
            if not df_filtrado.empty:
                row_c = df_filtrado.iloc[0]
                # ... aquí continúa tu código que usa row_c ...
            else:
                st.warning("⚠️ No se pudo cargar el detalle del contrato.")

            
            st.divider()
            c1, c2 = st.columns(2)
            sel_cid  = c1.selectbox("Contrato", df_cont["ID_Contrato"].tolist())
            row_c    = df_cont[df_cont["ID_Contrato"] == sel_cid].iloc[0]
            if c1.button("🚨 Finalizar Contrato"):
                db_query("UPDATE contratos SET activo=0 WHERE id=%s", (sel_cid,), commit=True); st.rerun()
            with c2:
                st.markdown("**🔄 Renovar con Continuidad**")
                meses_r = st.number_input("Meses a renovar", 1, 60, 6, key="r_meses")
                if st.button("🚀 Ejecutar Renovación"):
                    try:
                        f_ini_n = pd.to_datetime(row_c["Fin"]).date() + timedelta(days=1)
                        f_fin_n = f_ini_n + relativedelta(months=int(meses_r))
                        db_query("UPDATE contratos SET activo=0 WHERE id=%s", (sel_cid,), commit=True)
                        nuevo_id = db_query(
                            "INSERT INTO contratos (id_inmueble,id_inquilino,fecha_inicio,fecha_fin,monto_alquiler,activo)"
                            " VALUES (%s,%s,%s,%s,%s,1)",
                            (int(row_c["id_inmueble"]),int(row_c["id_inquilino"]),
                             f_ini_n, f_fin_n, int(row_c["Alq_Maestro"])), commit=True)
                        for conc, monto in [("Alquiler (Renov)", int(row_c["Alq_Maestro"])),
                                            ("Depósito (Renov)", int(row_c["Dep_Maestro"])),
                                            ("Gasto Cto (Renov)",int(row_c["Con_Maestro"]))]:
                            db_query("INSERT INTO deudas (id_contrato,concepto,monto_debe,monto_pago,pagado) VALUES (%s,%s,%s,0,0)",
                                     (nuevo_id, conc, monto), commit=True)
                        st.success(f"Renovado. Nuevo contrato #{nuevo_id} (desde {f_ini_n})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en renovación: {e}")

    # --- TAB 5: BACKUP ---
    with t5:
        st.subheader("💾 Backup y Restauración")
        c_exp, c_imp, c_res = st.columns(3)
        with c_exp:
            st.write("**Exportar**")
            if st.button("📂 Preparar Respaldo"):
                try:
                    buf = io.BytesIO()
                    tablas_map = [("bloques","Inmuebles"),("inmuebles","Unidades"),
                                  ("inquilinos","Inquilinos"),("contratos","Contratos"),("deudas","Deudas"),
                                  ("desarrollos","Loteos"),("lotes","Lotes_Inv"),
                                  ("compradores","Compradores"),("ventas_lotes","Ventas"),("cuotas_lotes","Cuotas")]
                    with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
                        for tabla, hoja in tablas_map:
                            df_t = db_query(f"SELECT * FROM {tabla}")
                            if df_t is not None:
                                df_t.to_excel(w, sheet_name=hoja, index=False)
                    st.session_state["backup"] = buf.getvalue()
                    st.success("✅ Listo.")
                except Exception as e:
                    st.error(f"Error: {e}")
            if st.session_state.get("backup"):
                st.download_button("📥 Descargar Excel", st.session_state["backup"],
                                   f"Backup_{date.today()}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                   key="dl_bak")
        with c_imp:
            st.write("**Restaurar**")
            arch = st.file_uploader("Subir .xlsx", type=["xlsx"], key="rest_up")
            if arch and st.button("🚀 Restaurar"):
                try:
                    engine = obtener_engine()
                    dfs    = pd.read_excel(arch, sheet_name=None)
                    mapa   = {"Inmuebles":"bloques","Unidades":"inmuebles","Inquilinos":"inquilinos",
                              "Contratos":"contratos","Deudas":"deudas","Loteos":"desarrollos",
                              "Lotes_Inv":"lotes","Compradores":"compradores",
                              "Ventas":"ventas_lotes","Cuotas":"cuotas_lotes"}
                    prog = st.empty()
                    with engine.begin() as conn:
                        for hoja, tabla in mapa.items():
                            if hoja in dfs:
                                prog.write(f"⏳ {hoja}…")
                                conn.execute(text(f'TRUNCATE TABLE "{tabla}" RESTART IDENTITY CASCADE'))
                                dfs[hoja].to_sql(tabla, engine, if_exists="append", index=False, method="multi", chunksize=100)
                    st.success("✅ Restauración completa.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        with c_res:
            st.write("**Limpiar Todo**")
            if st.button("🗑️ Vaciar BD"):
                try:
                    engine = obtener_engine()
                    with engine.begin() as conn:
                        for t in ["cuotas_lotes","ventas_lotes","compradores","lotes","desarrollos",
                                  "deudas","contratos","inmuebles","inquilinos","bloques"]:
                            conn.execute(text(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE'))
                    st.success("✅ Base limpia."); st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # --- TAB 6: ALQUILADOS ---
    with t6:
        st.subheader("📋 Ocupación Actual")
        df_alq = db_query("""
            SELECT b.nombre AS Inmueble, i.tipo AS Unidad,
                   iq.nombre AS Inquilino, iq.procedencia AS Domicilio, iq.celular AS WhatsApp,
                   COALESCE((SELECT SUM(monto_debe-COALESCE(monto_pago,0))
                             FROM deudas WHERE id_contrato=c.id AND pagado=0),0) AS Saldo
            FROM contratos c
            JOIN inmuebles i ON c.id_inmueble=i.id
            JOIN bloques b ON i.id_bloque=b.id
            JOIN inquilinos iq ON c.id_inquilino=iq.id
            WHERE c.activo=1 ORDER BY b.nombre""")
        if df_alq is not None and not df_alq.empty:
            # --- 1. CONSULTA DE SALDOS CON ALIAS EXPLÍCITO ---
            # Aseguramos que el cálculo de la deuda se llame "Saldo"
            query_saldos = """
                SELECT 
                    d.id,
                    iq.nombre as "Inquilino",
                    d.concepto as "Concepto",
                    (d.monto_debe - d.monto_pago) as "Saldo"
                FROM deudas d
                JOIN contratos c ON d.id_contrato = c.id
                JOIN inquilinos iq ON c.id_inquilino = iq.id
                WHERE d.pagado = 0
            """

            df_v = db_query(query_saldos)

            # --- 2. PROCESAMIENTO SEGURO (Línea 814 corregida) ---
            if df_v is not None and not df_v.empty:
                # Verificamos que la columna exista antes de aplicar el formato
                if "Saldo" in df_v.columns:
                    df_v["Saldo_Display"] = df_v["Saldo"].apply(
                        lambda x: f"🔴 {f_m(x)}" if x > 0 else "🟢 Al día"
                    )
                    
                st.dataframe(
                    df_v[["Inquilino", "Concepto", "Saldo_Display"]], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.info("✅ No hay saldos pendientes para las unidades seleccionadas.")
                
    # --- TAB 7: GENERACIÓN MENSUAL ---
    with t7:
        st.subheader("⚙️ Generación de Deudas Mensuales")
        with st.form("f_gen"):
            meses_lista = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                           "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
            mes  = st.selectbox("Mes",  meses_lista)
            anio = st.number_input("Año", value=date.today().year)
            if st.form_submit_button("Ejecutar Generación"):
                conts = db_query("SELECT id, monto_alquiler FROM contratos WHERE activo=1")
                if conts is not None and not conts.empty:
                    conc = f"Alquiler {mes} {int(anio)}"
                    generados = 0
                    for _, c in conts.iterrows():
                        existe = db_query("SELECT id FROM deudas WHERE id_contrato=%s AND concepto=%s",
                                          (int(c["id"]), conc))
                        if existe is None or existe.empty:
                            db_query("INSERT INTO deudas (id_contrato,concepto,monto_debe,monto_pago,pagado) VALUES (%s,%s,%s,0,0)",
                                     (int(c["id"]), conc, int(c["monto_alquiler"])), commit=True)
                            generados += 1
                    st.success(f"✅ {generados} cargos generados para {conc}.")
                else:
                    st.warning("No hay contratos activos.")

# ==============================================================================
# 7. LOTES
# ==============================================================================
elif menu == "🌳 Lotes":
    st.header("🌳 Gestión y Comercialización de Lotes (U$D)")
    t_l1, t_l2, t_l3, t_l4, t_l5 = st.tabs([
        "🏗️ Loteos", "📏 Inventario", "👤 Compradores", "🤝 Ventas", "💰 Cobranzas"
    ])

    # --- Loteos ---
    with t_l1:
        st.subheader("Nombres de Loteos")
        with st.form("f_loteo", clear_on_submit=True):
            n_name = st.text_input("Nombre del Loteo")
            n_ubic = st.text_input("Ubicación / Ruta")
            n_loc  = st.text_input("Localidad")
            if st.form_submit_button("💾 Guardar"):
                if n_name:
                    db_query("INSERT INTO desarrollos (nombre,ubicacion,localidad) VALUES (%s,%s,%s)",
                             (n_name,n_ubic,n_loc), commit=True)
                    st.success("✅ Loteo guardado."); st.rerun()
        df_lot = db_query("SELECT nombre AS Loteo, ubicacion AS Ubicacion, localidad AS Localidad FROM desarrollos")
        if df_lot is not None and not df_lot.empty:
            st.dataframe(df_lot, use_container_width=True, hide_index=True)

    # --- Inventario Lotes ---
    with t_l2:
        st.subheader("Inventario de Lotes")
        df_d = db_query("SELECT id, nombre FROM desarrollos ORDER BY nombre")
        if df_d is None or df_d.empty:
            st.warning("Primero cargue un Loteo en la pestaña anterior.")
        else:
            with st.expander("📝 Cargar Nuevo Lote", expanded=True):
                with st.form("f_lote", clear_on_submit=True):
                    id_d = st.selectbox("Loteo", df_d["id"],
                                        format_func=lambda x: df_d[df_d["id"]==x]["nombre"].values[0])
                    c1,c2,c3 = st.columns(3)
                    lt = c1.text_input("Nro Lote"); mz = c2.text_input("Manzana")
                    titular = c3.text_input("Titular Cedente")
                    f1,f2,f3,f4 = st.columns(4)
                    m2_v  = f1.number_input("M²", min_value=0.0, step=0.01, format="%.2f")
                    fre   = f2.number_input("Frente (m)", min_value=0.0, step=0.01, format="%.2f")
                    fon   = f3.number_input("Fondo (m)",  min_value=0.0, step=0.01, format="%.2f")
                    amoj  = f4.selectbox("Amojonamiento", ["NO","SI"])
                    s1,s2 = st.columns(2)
                    serv  = s1.multiselect("Servicios", ["LUZ","AGUA","INTERNET","GAS"])
                    c_am  = s2.number_input("Costo Amojon.", min_value=0, step=1)
                    st.markdown("---")
                    p1,p2 = st.columns([2,1])
                    p_cont = p1.number_input("Precio Contado", min_value=0, step=1)
                    m_cont = p2.selectbox("Moneda", ["U$D","PESOS"], key="mc1")
                    e1,e2 = st.columns([2,1])
                    p_ent  = e1.number_input("Entrega",    min_value=0, step=1)
                    m_ent  = e2.selectbox("Moneda",  ["PESOS","U$D"], key="me1")
                    q1,q2,q3 = st.columns([1,2,1])
                    cant_q = q1.number_input("Cuotas", min_value=0, value=12)
                    val_q  = q2.number_input("Valor Cuota", min_value=0, step=1)
                    mon_q  = q3.selectbox("Moneda", ["U$D","PESOS"], key="mq1")
                    obs   = st.text_area("Observaciones")
                    if st.form_submit_button("💾 Guardar Lote"):
                        db_query("""INSERT INTO lotes
                            (id_desarrollo,nro_lote,manzana,titular_cedente,metros_cuadrados,
                             frente,fondo,amojonamiento,costo_amojonamiento,servicios,
                             precio_contado,moneda_contado,entrega_monto,moneda_entrega,
                             cuotas_monto,moneda_cuotas,cant_cuotas,observaciones)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                            (id_d,lt,mz,titular,m2_v,fre,fon,amoj,c_am,", ".join(serv),
                             p_cont,m_cont,p_ent,m_ent,val_q,mon_q,cant_q,obs), commit=True)
                        st.success("✅ Lote guardado."); st.rerun()

            df_lotes = db_query("""
                SELECT l.id AS ID, d.nombre AS Loteo, l.nro_lote AS Lote, l.manzana AS Mz,
                       l.metros_cuadrados AS M2, l.amojonamiento AS Amoj, l.estado AS Estado
                FROM lotes l JOIN desarrollos d ON l.id_desarrollo=d.id ORDER BY l.id DESC""")
            if df_lotes is not None:
                st.dataframe(df_lotes, use_container_width=True, hide_index=True)

    # --- Compradores ---
    with t_l3:
        st.subheader("Registro de Compradores")
        with st.expander("➕ Nuevo Comprador", expanded=True):
            with st.form("f_comp", clear_on_submit=True):
                c1,c2 = st.columns(2)
                nc = c1.text_input("Nombre / Razón Social"); dc = c1.text_input("DNI / CUIT")
                cc = c2.text_input("Celular");               mc = c2.text_input("Email")
                domc = st.text_input("Domicilio")
                if st.form_submit_button("💾 Guardar"):
                    if nc.strip():
                        db_query("INSERT INTO compradores (nombre,dni_cuit,celular,domicilio,email) VALUES (%s,%s,%s,%s,%s)",
                                 (nc,dc,cc,domc,mc), commit=True)
                        st.success("✅ Comprador guardado."); st.rerun()
                    else:
                        st.error("El nombre es obligatorio.")
        df_comps = db_query("SELECT id AS ID, nombre AS Nombre, dni_cuit AS DNI_CUIT, celular AS Celular, email AS Email FROM compradores ORDER BY id DESC")
        if df_comps is not None and not df_comps.empty:
            st.dataframe(df_comps, use_container_width=True, hide_index=True)
            with st.expander("🗑️ Eliminar Comprador"):
                id_del = st.number_input("ID a eliminar", min_value=1, step=1)
                if st.button("❌ Eliminar"):
                    db_query("DELETE FROM compradores WHERE id=%s", (id_del,), commit=True)
                    st.warning(f"ID {id_del} eliminado."); st.rerun()

    # --- Ventas ---
    with t_l4:
        st.subheader("Registrar Venta de Lote")
        ll = db_query("""
            SELECT l.id, d.nombre||' - Mz: '||l.manzana||' - Lote: '||l.nro_lote AS ref,
                   l.precio_contado, l.entrega_monto, l.cant_cuotas, l.cuotas_monto, l.moneda_cuotas
            FROM lotes l JOIN desarrollos d ON l.id_desarrollo=d.id WHERE l.estado='Libre'""")
        comps = db_query("SELECT id, nombre FROM compradores ORDER BY nombre")
        if ll is None or ll.empty:
            st.info("No hay lotes libres disponibles.")
        elif comps is None or comps.empty:
            st.info("No hay compradores registrados.")
        else:
            with st.form("f_venta"):
                id_l = st.selectbox("Lote", ll["id"],
                                    format_func=lambda x: ll[ll["id"]==x]["ref"].values[0])
                id_c = st.selectbox("Comprador", comps["id"],
                                    format_func=lambda x: comps[comps["id"]==x]["nombre"].values[0])
                sug  = ll[ll["id"]==id_l].iloc[0]
                c1,c2 = st.columns(2)
                f_venta = c1.date_input("Fecha Venta", date.today())
                f_1ra   = c2.date_input("1ra Cuota",   date.today())
                c1,c2,c3 = st.columns(3)
                v_tot  = c1.number_input("Precio Total U$D", value=int(sug["precio_contado"]))
                v_ent  = c2.number_input("Entrega",          value=int(sug["entrega_monto"]))
                v_cant = c3.number_input("Cant. Cuotas",     value=int(sug["cant_cuotas"]))
                v_mon  = c1.number_input("Valor Cuota",      value=int(sug["cuotas_monto"]))
                if st.form_submit_button("🤝 Confirmar Venta"):
                    v_id = db_query("""INSERT INTO ventas_lotes
                        (id_lote,id_comprador,fecha_venta,monto_total_usd,entrega_usd,cantidad_cuotas,monto_cuota_usd)
                        VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                        (id_l,id_c,f_venta,v_tot,v_ent,v_cant,v_mon), commit=True)
                    for i in range(1, v_cant+1):
                        venc = f_1ra + timedelta(days=30*(i-1))
                        db_query("INSERT INTO cuotas_lotes (id_venta,nro_cuota,monto_usd,fecha_vencimiento,pagado) VALUES (%s,%s,%s,%s,0)",
                                 (v_id,i,v_mon,venc), commit=True)
                    db_query("UPDATE lotes SET estado='Vendido' WHERE id=%s", (id_l,), commit=True)
                    st.success("✅ Venta registrada y cuotas generadas."); st.rerun()

    # --- Cobranzas Lotes ---
    with t_l5:
        st.subheader("Cobranzas de Lotes")
        sub1, sub2 = st.tabs(["💵 Cobrar Cuota", "📊 Consultas"])

        with sub1:
            df_q = db_query("""
                SELECT cl.id, d.nombre AS Loteo, l.manzana, l.nro_lote,
                       co.nombre AS Cliente, cl.nro_cuota, cl.monto_usd, cl.fecha_vencimiento
                FROM cuotas_lotes cl
                JOIN ventas_lotes vl ON cl.id_venta=vl.id
                JOIN lotes l ON vl.id_lote=l.id
                JOIN desarrollos d ON l.id_desarrollo=d.id
                JOIN compradores co ON vl.id_comprador=co.id
                WHERE cl.pagado=0 ORDER BY cl.fecha_vencimiento""")
            if df_q is not None and not df_q.empty:
                with st.form("f_cobro_lote"):
                    sel_q = st.selectbox("Cuota", df_q["id"].tolist(),
                                         format_func=lambda x: (
                                             f"{df_q[df_q['id']==x]['Cliente'].values[0]} | "
                                             f"{df_q[df_q['id']==x]['Loteo'].values[0]} "
                                             f"Mz {df_q[df_q['id']==x]['manzana'].values[0]} "
                                             f"Lote {df_q[df_q['id']==x]['nro_lote'].values[0]} | "
                                             f"Q:{df_q[df_q['id']==x]['nro_cuota'].values[0]} | "
                                             f"Vence: {df_q[df_q['id']==x]['fecha_vencimiento'].values[0]}"))
                    c_mon = st.number_input("Monto a cobrar",
                                            value=float(df_q[df_q["id"]==sel_q]["monto_usd"].values[0]))
                    c1, c2 = st.columns(2)
                    if c1.form_submit_button("✅ Registrar Pago"):
                        db_query("UPDATE cuotas_lotes SET pagado=1,monto_pagado_usd=%s,fecha_pago=%s WHERE id=%s",
                                 (c_mon, date.today(), sel_q), commit=True)
                        st.success("✅ Pago registrado."); st.rerun()
                    if c2.form_submit_button("📁 Marcar Pagada (Histórico)"):
                        db_query("UPDATE cuotas_lotes SET pagado=1,monto_pagado_usd=%s,fecha_pago=%s WHERE id=%s",
                                 (c_mon, date.today(), sel_q), commit=True)
                        st.success("✅ Marcada como pagada."); st.rerun()
            else:
                st.info("No hay cuotas pendientes.")

        with sub2:
            st.subheader("🔍 Filtros de Cartera")
            df_dev = db_query("SELECT nombre FROM desarrollos")
            lista_l = ["Todos"] + (df_dev["nombre"].tolist() if df_dev is not None else [])
            c1,c2,c3 = st.columns(3)
            sel_loteo = c1.selectbox("Loteo", lista_l)
            sel_mz    = c2.text_input("Manzana")
            sel_lt    = c3.text_input("Nro Lote")
            c4,c5,c6 = st.columns(3)
            meses_n   = ["Todos","01","02","03","04","05","06","07","08","09","10","11","12"]
            sel_mes   = c4.selectbox("Mes Vencimiento", meses_n)
            sel_anio  = c5.number_input("Año", min_value=2020, max_value=2035, value=date.today().year)
            sel_est   = c6.selectbox("Estado", ["Todas","Pagadas","Impagas (A vencer)","VENCIDAS (Mora)"])

            hoy_s = date.today().strftime("%Y-%m-%d")
            q_r = f"""
                SELECT d.nombre AS Loteo, l.manzana AS Mz, l.nro_lote AS Lote,
                       co.nombre AS Cliente, cl.nro_cuota AS Cuota,
                       cl.monto_usd AS Monto, cl.fecha_vencimiento AS Vencimiento,
                       CASE WHEN cl.pagado=1 THEN 'PAGADA'
                            WHEN cl.pagado=0 AND cl.fecha_vencimiento < '{hoy_s}' THEN 'VENCIDA'
                            ELSE 'A VENCER' END AS Estado
                FROM cuotas_lotes cl
                JOIN ventas_lotes vl ON cl.id_venta=vl.id
                JOIN lotes l ON vl.id_lote=l.id
                JOIN desarrollos d ON l.id_desarrollo=d.id
                JOIN compradores co ON vl.id_comprador=co.id
                WHERE 1=1"""
            if sel_loteo != "Todos": q_r += f" AND d.nombre='{sel_loteo}'"
            if sel_mz:               q_r += f" AND l.manzana='{sel_mz}'"
            if sel_lt:               q_r += f" AND l.nro_lote='{sel_lt}'"
            if sel_mes != "Todos":
                q_r += f" AND TO_CHAR(cl.fecha_vencimiento,'MM')='{sel_mes}'"
                q_r += f" AND TO_CHAR(cl.fecha_vencimiento,'YYYY')='{int(sel_anio)}'"
            if sel_est == "Pagadas":
                q_r += " AND cl.pagado=1"
            elif sel_est == "Impagas (A vencer)":
                q_r += f" AND cl.pagado=0 AND cl.fecha_vencimiento >= '{hoy_s}'"
            elif sel_est == "VENCIDAS (Mora)":
                q_r += f" AND cl.pagado=0 AND cl.fecha_vencimiento < '{hoy_s}'"

            df_f = db_query(q_r)
            if df_f is not None and not df_f.empty:
                st.write(f"{len(df_f)} cuotas encontradas.")
                df_fv = df_f.copy()
                df_fv["Monto"] = df_fv["Monto"].apply(f_m)
                st.dataframe(df_fv, use_container_width=True, hide_index=True)
                total_f = df_f["Monto"].sum()
                c1, c2 = st.columns([2,1])
                c1.metric("Total", f_m(total_f))
                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="xlsxwriter") as w:
                    df_f.to_excel(w, index=False, sheet_name="Cobranzas")
                c2.download_button("📥 Exportar Excel", buf.getvalue(),
                                   f"Cobranzas_{sel_loteo}_{sel_mes}_{int(sel_anio)}.xlsx",
                                   "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.info("Sin resultados para los filtros aplicados.")
