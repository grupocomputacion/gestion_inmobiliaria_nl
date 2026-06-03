import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import io
from fpdf import FPDF

# Forzamos a que estas variables existan desde el segundo 1
if 'uid' not in locals(): uid = None
if 'iid' not in locals(): iid = None
if 'sel_u' not in locals(): sel_u = None

# --- INICIALIZACIÓN DE SEGURIDAD (Línea 15 aprox) ---
if 'pdf_listo' not in st.session_state:
    st.session_state['pdf_listo'] = None
if 'id_listo' not in st.session_state:
    st.session_state['id_listo'] = None

# --- ESTILO CSS REFORZADO (V.10.0) ---
st.markdown("""
    <style>
        /* Fondo del Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1E1E1E !important;
        }
        /* Texto de los botones del menú en blanco puro */
        [data-testid="stSidebar"] .stRadio div label p {
            color: white !important;
            font-size: 1.1rem !important;
            font-weight: 500 !important;
        }
        /* Color de los íconos del menú */
        [data-testid="stSidebar"] .stRadio div label span {
            color: white !important;
        }
        /* Hover: cuando pasas el mouse por encima */
        [data-testid="stSidebar"] .stRadio div label:hover {
            background-color: #333333 !important;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)


# 1. DEFINICIÓN DE LA CLASE PDF (FUERA DEL MENÚ)
class PDFRecibo(FPDF):
    def header(self):
        if os.path.exists("alquileres.jpg"):
            self.image("alquileres.jpg", 10, 8, 30)
        self.set_font('Arial', 'B', 16)
        self.cell(80)
        self.cell(30, 10, 'RECIBO OFICIAL DE PAGO', 0, 0, 'C')
        self.ln(20)

# --- FUNCIONES DE SOPORTE CRÍTICAS ---

def cl(texto):
    """Limpia el formato para guardar en la DB como número puro"""
    try:
        if isinstance(texto, (int, float)):
            return int(texto)
        # Quitamos el punto de miles para que Python lo procese como nro
        return int(str(texto).replace(".", "").replace("$", "").replace("U$D", "").strip())
    except:
        return 0

def f_m(valor):
    """Formatea montos: Sin decimales y con punto en miles (Ej: 1.500.000)"""
    try:
        if valor is None or valor == "":
            return "0"
        # Quitamos decimales convirtiendo a int y formateamos con punto
        return f"{int(float(valor)):,}".replace(",", ".")
    except:
        return "0"

def db_query(query, params=(), commit=False):
    import sqlite3
    import pandas as pd
    conn = conectar_db() # Usamos la función que creamos al principio
    if conn:
        cur = conn.cursor()
        # ACÁ VA TU INSERT: Recordá cambiar los ? por %s manualmente si no usás db_query
        cur.execute("INSERT INTO gestiones (fecha, propiedad, monto) VALUES (%s, %s, %s)", (f, p, m))
        conn.commit() # Guardamos los cambios
        cur.close()
        conn.close() # Cerramos el caño (VITAL para no saturar Supabase)
        cur = conn.cursor()
    try:
        if commit:
            cur.execute(query, params)
            conn.commit()
            last_id = cur.lastrowid
            conn.close()
            return last_id
        else:
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df
    except Exception as e:
        st.error(f"Error en la base de datos: {e}")
        conn.close()
        return None


# --- ACTUALIZACIÓN ESTRUCTURA LOTES (V.2.5) ---
db_query("""CREATE TABLE IF NOT EXISTS lotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_desarrollo INTEGER,
    manzana TEXT,
    nro_lote TEXT,
    metros_cuadrados REAL,
    frente REAL,
    fondo REAL,
    servicios TEXT,
    observaciones TEXT,
    precio_contado REAL,
    moneda_contado TEXT DEFAULT 'U$D',
    entrega_monto REAL,
    moneda_entrega TEXT DEFAULT 'PESOS',
    cuotas_monto REAL,
    moneda_cuotas TEXT DEFAULT 'U$D',
    cant_cuotas INTEGER,
    amojonamiento TEXT DEFAULT 'NO',
    costo_amojonamiento REAL DEFAULT 0,
    titular_cedente TEXT,
    estado TEXT DEFAULT 'Libre'
)""", commit=True)
    

# ==========================================
# 1. CONFIGURACIÓN E IDENTIDAD (V.74 - ESTILO 3D)
# ==========================================
st.set_page_config(page_title="NL INMOBILIARIA - V.5.0", layout="wide")
st.cache_data.clear()

st.markdown("""
    <style>
        /* 1. BARRA LATERAL (FONDO BLANCO Y SOMBRA 3D) */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF !important;
            border-right: 1px solid #E0E0E0;
            box-shadow: 4px 0px 15px rgba(0, 0, 0, 0.1);
        }

        /* 2. TEXTO DEL MENÚ (NEGRO Y PROFESIONAL) */
        [data-testid="stSidebar"] .stRadio div label p {
            color: #1A1A1A !important;
            font-size: 1.05rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease;
        }

        /* 3. EFECTO 3D EN BOTONES DEL MENÚ (HOVER) */
        [data-testid="stSidebar"] .stRadio div label {
            background-color: #F8F9FA;
            border-radius: 8px;
            margin-bottom: 5px;
            padding: 8px 12px;
            border: 1px solid transparent;
            box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
        }

        [data-testid="stSidebar"] .stRadio div label:hover {
            background-color: #FFFFFF !important;
            border: 1px solid #D4AF37 !important;
            box-shadow: 3px 3px 10px rgba(212, 175, 55, 0.2);
            transform: translateY(-2px); /* Efecto de elevación 3D */
        }

        /* 4. BOTONES PRINCIPALES (DORADO PREMIUM) */
        .stButton>button {
            background-color: #D4AF37;
            color: #000000;
            font-weight: bold;
            width: 100%;
            border-radius: 8px;
            border: none;
            box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
            transition: all 0.2s;
        }

        .stButton>button:hover {
            background-color: #B8952E;
            box-shadow: 0px 6px 12px rgba(0, 0, 0, 0.2);
            transform: translateY(-1px);
        }

        /* 5. TÍTULOS */
        h1, h2, h3, h4 { 
            color: #1A1A1A; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            border-bottom: 2px solid #D4AF37;
            padding-bottom: 10px;
        }

        /* Ajuste para el texto informativo del sidebar */
        [data-testid="stSidebar"] .stMarkdown p {
            color: #666666 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. MOTOR DE DATOS — SUPABASE (nube) + SQLITE (local) (V.7.0)
# ==========================================
#
# CONFIGURACIÓN (hacer UNA sola vez):
#  1. Crear cuenta gratis en https://supabase.com
#  2. Nuevo proyecto → Settings → Database → URI (copiala)
#  3. En Streamlit Cloud → Settings → Secrets → pegar:
#       [supabase]
#       url = "postgresql://postgres:PASSWORD@db.XXXX.supabase.co:5432/postgres"
#  4. Para correr LOCAL: crear .streamlit/secrets.toml con lo mismo
#
# El sistema detecta automáticamente si hay Supabase y lo usa.
# Sin secrets → SQLite local (tu notebook).
#

import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import io
from fpdf import FPDF
from sqlalchemy import create_engine, text

# --- CONEXIÓN ROBUSTA ---
def conectar_db():
    try:
        conf = st.secrets["database"]
        return psycopg2.connect(
            host=conf["host"],
            port=conf["port"],
            database=conf["database"],
            user=conf["user"],
            password=conf["password"],
            connect_timeout=10
        )
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return None

def obtener_engine():
    c = st.secrets["database"]
    url = f"postgresql://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['database']}"
    return create_engine(url, pool_pre_ping=True)

# Reemplazo de db_query para que sea compatible con Postgres
def db_query(query, params=(), commit=False):
    conn = conectar_db()
    if not conn: return None
    try:
        if commit:
            cur = conn.cursor()
            # Cambiamos placeholders de ? a %s dinámicamente si es necesario
            query = query.replace('?', '%s')
            cur.execute(query, params)
            conn.commit()
            cur.close()
            conn.close()
            return True
        else:
            query = query.replace('?', '%s')
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df
    except Exception as e:
        st.error(f"Error en DB: {e}")
        if conn: conn.close()
        return None


def mantenimiento_base():
    """Crea todas las tablas en Supabase si no existen. Seguro de ejecutar siempre."""
    tablas_ddl = [
        """CREATE TABLE IF NOT EXISTS bloques (
            id SERIAL PRIMARY KEY, nombre TEXT, direccion TEXT,
            barrio TEXT, localidad TEXT)""",
        """CREATE TABLE IF NOT EXISTS inquilinos (
            id SERIAL PRIMARY KEY, nombre TEXT, dni TEXT, celular TEXT,
            procedencia TEXT, grupo TEXT, emergencia TEXT)""",
        """CREATE TABLE IF NOT EXISTS inmuebles (
            id SERIAL PRIMARY KEY, id_bloque INTEGER, tipo TEXT,
            precio_alquiler BIGINT DEFAULT 0, costo_contrato BIGINT DEFAULT 0,
            deposito_base BIGINT DEFAULT 0)""",
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
            id SERIAL PRIMARY KEY, id_desarrollo INTEGER, manzana TEXT,
            nro_lote TEXT, metros_cuadrados REAL DEFAULT 0, frente REAL DEFAULT 0,
            fondo REAL DEFAULT 0, servicios TEXT, observaciones TEXT,
            precio_contado REAL DEFAULT 0, moneda_contado TEXT DEFAULT 'U$D',
            entrega_monto REAL DEFAULT 0, moneda_entrega TEXT DEFAULT 'PESOS',
            cuotas_monto REAL DEFAULT 0, moneda_cuotas TEXT DEFAULT 'U$D',
            cant_cuotas INTEGER DEFAULT 0, amojonamiento TEXT DEFAULT 'NO',
            costo_amojonamiento REAL DEFAULT 0, titular_cedente TEXT,
            estado TEXT DEFAULT 'Libre')""",
        """CREATE TABLE IF NOT EXISTS compradores (
            id SERIAL PRIMARY KEY, nombre TEXT, dni_cuit TEXT,
            celular TEXT, domicilio TEXT, email TEXT)""",
        """CREATE TABLE IF NOT EXISTS ventas_lotes (
            id SERIAL PRIMARY KEY, id_lote INTEGER, id_comprador INTEGER,
            fecha_venta DATE, monto_total_usd REAL DEFAULT 0,
            entrega_usd REAL DEFAULT 0, cantidad_cuotas INTEGER DEFAULT 0,
            monto_cuota_usd REAL DEFAULT 0, estado TEXT DEFAULT 'Activa')""",
        """CREATE TABLE IF NOT EXISTS cuotas_lotes (
            id SERIAL PRIMARY KEY, id_venta INTEGER, nro_cuota INTEGER,
            monto_usd REAL DEFAULT 0, fecha_vencimiento DATE,
            pagado INTEGER DEFAULT 0, monto_pagado_usd REAL DEFAULT 0,
            fecha_pago DATE)""",
    ]
    for ddl in tablas_ddl:
        db_query(ddl, commit=True)

# Crear tablas al iniciar (idempotente)
mantenimiento_base()

# (tablas creadas por mantenimiento_base al inicio)

# ==========================================
# 3. GENERADOR DE PDF (TEXTO LEGAL ÍNTEGRO V.5.3)
# ==========================================
def generar_pdf_v5(datos_u, datos_i, f_inicio, m_alq, m_dep, m_con, uso_contrato):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Logo (Si existe)
    if os.path.exists("alquileres.jpg"):
        pdf.image("alquileres.jpg", 10, 8, 30)
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'CONTRATO DE LOCACION TEMPORARIA (3 MESES)', 0, 1, 'C')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 10)
    hoy = date.today()
    meses_nom = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    
    # --- EXTRACCIÓN SEGURA DE DATOS (Fix para evitar el error 'direccion') ---
    nom_i = str(datos_i.get('nombre', 'S/D')).upper()
    dni_i = str(datos_i.get('dni', 'S/D'))
    # Buscamos dirección en cualquier columna posible
    dir_i = str(datos_i.get('procedencia', datos_i.get('domicilio', datos_i.get('direccion', 'S/D'))))
    
    # --- Datos de la Unidad (V.75 - Búsqueda Total) ---
    # 1. Intentamos buscar 'direccion' (que debería venir del JOIN con bloques)
    dir_u = str(datos_u.get('direccion', 'S/D'))
    
    # 2. Si falló, buscamos 'nombre_edificio' o 'nombre' (alias del JOIN)
    if dir_u == "S/D":
        dir_u = str(datos_u.get('nombre_edificio', datos_u.get('nombre', 'S/D')))
    
    # 3. Si sigue fallando, buscamos 'ubicacion' o 'procedencia' (por las dudas)
    if dir_u == "S/D":
        dir_u = str(datos_u.get('ubicacion', datos_u.get('procedencia', 'S/D')))
        
    tipo_u = str(datos_u.get('tipo', 'Unidad Estándar'))
    

    # 2. TEXTO LEGAL EXACTO
    texto_legal = f"""Entre NL PROPIEDADES, CUIT 30-71884850-0 con domicilio en Av. Velez Sarsfield 745, B. Nueva Córdoba, Córdoba Capital, en adelante "EL LOCADOR" y por la otra parte {nom_i}, DNI {dni_i}, con domicilio en {dir_i}, en adelante "EL LOCATARIO", se celebra el presente contrato sujeto a las siguientes cláusulas:

1) OBJETO: Se alquila el inmueble ubicado en {dir_u}, destinado a uso {uso_contrato}. Unidad: {tipo_u}.

2) PLAZO: El contrato tendra una duración de TRES (3) MESES, iniciando el día {f_inicio.strftime('%d/%m/%Y')}.

3) PRECIO: El valor del alquiler por mes, sera de $ {f_m(cl(m_alq))}.

4) GARANTIA: Se recibe la suma de $ {f_m(cl(m_dep))}, en concepto de Garantía, la misma sera reintegrada al finalizar el contrato, el locatario debera dar previo aviso de 15 dias por escrito de la discontinuidad del alquiler una vez finalicen los 3 meses. En caso de que el inmueble presentara algun desperfecto (rotura, pintura, artefactos dañados, etc.) se utilizará el monto recibido para reparaciones. En caso de incumplimientos contractuales, el monto de la garantía quedará para el locador como resarcimiento.

5) GASTOS: Seran a cargo del locatario todos los servicios, tasas e impuestos que correspondan al uso del inmueble.

6) PROHIBICIONES: No se podrá cambiar la titularidad del contrato ni subalquilar total o parcialmente el inmueble. No se aceptan mascotas, ni menores de edad.

7) FIRMA: La firma del presente contrato tiene un costo administrativo de $ {f_m(cl(m_con))}.

8) MORA: Ante mora del pago del alquiler mensual, EL LOCATARIO debera desalojar el inmueble habitado, en un plazo no maximo a 15 dias de corrido.

El locatario declara recibir el inmueble en buen estado y se compromete a devolverlo en iguales condiciones.

En prueba de conformidad, se firman dos ejemplares de un mismo tenor en la ciudad de Cordoba, a los {hoy.day} dias del mes de {meses_nom[hoy.month-1]} del año {hoy.year}.
"""
    clean_text = texto_legal.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, clean_text)
    pdf.ln(10)
    
    # 4. BLOQUE DE FIRMAS
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(90, 5, 'LA LOCADORA - NL PROPIEDADES', 0, 0, 'L')
    pdf.cell(90, 5, 'EL LOCATARIO', 0, 1, 'R')
    pdf.ln(5)
    pdf.set_font('Arial', '', 9)
    pdf.cell(90, 8, 'Firma: __________________________', 0, 0, 'L')
    pdf.cell(90, 8, 'Firma: __________________________', 0, 1, 'R')
    pdf.cell(90, 8, 'Aclaracion: NL PROPIEDADES', 0, 0, 'L')
    pdf.cell(90, 8, f"Aclaración: {nom_i}", 0, 1, 'R')
    pdf.cell(90, 8, 'DNI/CUIT: 30-71884850-0', 0, 0, 'L')
    pdf.cell(90, 8, f"DNI: {dni_i}", 0, 1, 'R')

# Final de generar_pdf_v5
    res_pdf = pdf.output(dest='S')
    # Si la librería devuelve string, convertimos a bytes. Si no, aseguramos bytes.
    return res_pdf.encode('latin-1') if isinstance(res_pdf, str) else bytes(res_pdf)


def generar_pdf_lote(datos_pago, datos_comprador, datos_lote):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    if os.path.exists("alquileres.jpg"):
        pdf.image("alquileres.jpg", 10, 8, 33)
    
    pdf.set_font('Arial', 'B', 15)
    pdf.cell(80)
    pdf.cell(30, 10, 'RECIBO DE PAGO - LOTES', 0, 0, 'C')
    pdf.ln(20)
    
    # Datos de la Empresa y Fecha
    pdf.set_font('Arial', '', 10)
    pdf.cell(100, 7, "NL INMOBILIARIA - GESTIÓN DE LOTEO", 0, 0, 'L')
    pdf.cell(90, 7, f"Fecha: {date.today().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.ln(10)
    
    # Cuerpo del Recibo
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 8, f"RECIBIMOS DE: {datos_comprador['nombre'].upper()}", 1, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font('Arial', '', 11)
    pdf.cell(0, 8, f"La suma de: U$D {f_m(datos_pago['monto'])} (Dólares Estadounidenses)", 0, 1, 'L')
    pdf.cell(0, 8, f"En concepto de: {datos_pago['concepto']}", 0, 1, 'L')
    pdf.cell(0, 8, f"Referencia: Manzana {datos_lote['manzana']} - Lote {datos_lote['nro_lote']}", 0, 1, 'L')
    pdf.ln(15)
    
    # Firma
    pdf.ln(20)
    pdf.cell(110)
    pdf.cell(80, 7, "_______________________________", 0, 1, 'C')
    pdf.cell(110)
    pdf.cell(80, 7, "Firma Autorizada", 0, 1, 'C')

    raw = pdf.output(dest='S')
    return bytes(raw) if isinstance(raw, (bytes, bytearray)) else raw.encode('latin-1')


# ==========================================
# 4. BARRA LATERAL
# ==========================================
with st.sidebar:
    if os.path.exists("alquileres.jpg"): st.image("alquileres.jpg", use_container_width=True)
    st.info("🚀 SISTEMA NL V.5.0")
    menu = st.radio("MENÚ:", ["🏠 Inventario", "📝 Nuevo Contrato", "💰 Cobranzas", "🚨 Morosos", "📊 Caja", "⚙️ Carga", "🌳 Lotes"])

# ==========================================
# 5. SECCIONES
# ==========================================


# ==========================================
# 1. INVENTARIO (V.13.0 - CÁLCULO DIRECTO)
# ==========================================
if menu == "🏠 Inventario":
    st.header("Inventario Global de Unidades")

    # --- 1. FILTROS DE VISTA ---
    c1, c2 = st.columns(2)
    df_bloques_filt = db_query("SELECT nombre FROM bloques")
    lista_inmuebles = ["Todos"] + df_bloques_filt['nombre'].tolist() if df_bloques_filt is not None else ["Todos"]
    sel_inmueble = c1.selectbox("🏢 Filtrar por Edificio:", lista_inmuebles)
    sel_estado = c2.selectbox("🔑 Filtrar por Disponibilidad:", ["Todos", "Libre", "Ocupado"])

    # --- 2. VALIDACIÓN DE COLUMNAS ---
    check_c = db_query("PRAGMA table_info(contratos)")
    cols_c = [col[1] for col in check_c] if check_c is not None else []
    # Usamos c.fecha_fin si existe, sino NULL
    col_f_sql = "c.fecha_fin" if "fecha_fin" in cols_c else "NULL"

    # --- 3. CONSULTA SQL ROBUSTA ---
    query_inv = f"""
        SELECT 
            b.nombre as Inmueble,
            i.tipo as Unidad,
            i.precio_alquiler as Alquiler,
            i.costo_contrato as Contrato,
            i.deposito_base as Deposito,
            c.fecha_inicio as Inicio,
            CASE 
                WHEN c.id IS NOT NULL THEN 'Ocupado'
                ELSE 'Libre'
            END as Estado,
            c.fecha_inicio,
            CASE 
                WHEN c.id IS NOT NULL THEN {col_f_sql}
                ELSE 'Inmediata'
            END as [Disponible Desde]
        FROM inmuebles i
        JOIN bloques b ON i.id_bloque = b.id
        LEFT JOIN contratos c ON i.id = c.id_inmueble AND c.activo = 1
        WHERE 1=1
    """
    
    if sel_inmueble != "Todos":
        query_inv += f" AND b.nombre = '{sel_inmueble}'"
    
    df_inv = db_query(query_inv)

    if df_inv is not None and not df_inv.empty:
        # Filtro de estado por código
        if sel_estado != "Todos":
            df_inv = df_inv[df_inv['Estado'] == sel_estado]

        # --- MÉTRICAS ---
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Unidades", len(df_inv))
        m2.metric("Ocupadas", len(df_inv[df_inv['Estado'] == 'Ocupado']))
        m3.metric("Libres", len(df_inv[df_inv['Estado'] == 'Libre']))

        st.write("---")

        # --- 4. LÓGICA DE CÁLCULO DE FECHAS ---
        df_show = df_inv.copy()
        
        # Formateo de montos
        for col in ['Alquiler', 'Contrato', 'Deposito']:
            df_show[col] = df_show[col].apply(f_m)

        def calcular_disponibilidad(row):
            f_ini = row.get('fecha_inicio')
            f_fin = row.get('Disponible Desde')

            try:
                # Si ya hay una fecha de fin válida en DB, la usamos
                if f_fin and str(f_fin).lower() not in ['none', 'nan', 'null', '', 'inmediata', 'sin fecha']:
                    return pd.to_datetime(f_fin).strftime('%Y-%m-%d')
                
                # Si no hay fin, calculamos Inicio + 3 meses (Exacto por calendario)
                if f_ini and str(f_ini).lower() not in ['none', 'nan', 'null', '']:
                    fecha_dt = pd.to_datetime(f_ini).date()
                    # relativedelta maneja correctamente meses de 31 días
                    resultado = fecha_dt + relativedelta(months=3)
                    return resultado.strftime('%Y-%m-%d')
                
                return "Inmediata"
            except:
                return "Inmediata"

        # Aplicamos el cálculo a la columna
        from dateutil.relativedelta import relativedelta
        df_show['Disponible Desde'] = df_show.apply(calcular_disponibilidad, axis=1)

        # Estilo visual de colores
        def color_estado(val):
            color = '#ff4b4b' if val == 'Ocupado' else '#28a745'
            return f'color: {color}; font-weight: bold'

        # Mostramos la tabla (quitamos fecha_inicio del visual)
        cols_finales = [c for c in df_show.columns if c != 'fecha_inicio']
        st.dataframe(
            df_show[cols_finales].style.map(color_estado, subset=['Estado']), 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("No se encontraron unidades.")



# ==========================================
# 2. NUEVO CONTRATO (V.72 - RESCATE)
# ==========================================
elif menu == "📝 Nuevo Contrato":
    st.header("Formalización de Contrato")

    u_raw = db_query("SELECT * FROM inmuebles")
    i_raw = db_query("SELECT * FROM inquilinos")

    if u_raw is not None and not u_raw.empty and i_raw is not None and not i_raw.empty:
        st.subheader("1. Selección de Unidad e Inquilino")
        c1, c2 = st.columns(2)
        
        dict_u = {str(row['tipo']): row['id'] for _, row in u_raw.iterrows()}
        u_sel = c1.selectbox("Seleccione Unidad", sorted(list(dict_u.keys())), key="u_v72")
        uid = dict_u[u_sel]
        
        dict_i = {str(row['nombre']): row['id'] for _, row in i_raw.iterrows()}
        i_sel = c2.selectbox("Seleccione Inquilino", sorted(list(dict_i.keys())), key="i_v72")
        iid = dict_i[i_sel]

        s_u = u_raw[u_raw['id'] == uid].iloc[0]
        s_i = i_raw[i_raw['id'] == iid].iloc[0]

        with st.form("f_v72"):
            st.subheader(f"📄 Datos: {u_sel}")
            col1, col2 = st.columns(2)
            fini = col1.date_input("Fecha Inicio", date.today())
            meses = col2.number_input("Meses", 1, 60, 6)

            # --- NUEVA LÍNEA: SELECCIÓN DE USO ---
            uso_sel = st.radio("Destino del inmueble:", ["Vivienda", "Comercial", "Vivienda / Comercial"], horizontal=True)
            # -------------------------------------            
            
            v1, v2, v3 = st.columns(3)
            ma = v1.text_input("Alquiler", f_m(s_u.get('precio_alquiler', 0)))
            md = v2.text_input("Depósito", f_m(s_u.get('deposito_base', 0)))
            mc = v3.text_input("Gastos", f_m(s_u.get('costo_contrato', 0)))

            if st.form_submit_button("✅ GUARDAR Y GENERAR"):
                try:
            # --- Cálculo de Fin de Contrato con Meses Reales (V.76) ---
                    from dateutil.relativedelta import relativedelta # Asegurate de tener esta librería

            # Reemplaza la línea de f_v por esta:
                    f_v = fini + relativedelta(months=int(meses))                    
                    val_p = s_i.get('procedencia', s_i.get('domicilio', 'No especificada'))

                    # A. INSERT DINÁMICO (Seguridad de columnas)
                    check_cols = db_query("PRAGMA table_info(contratos)")
                    cols_db = [c[1] for c in check_cols] if check_cols is not None else []
                    
                    # Armamos el query según lo que exista en TU base de datos
                    campos = ["id_inmueble", "id_inquilino", "fecha_inicio", "fecha_fin", "monto_alquiler", "activo"]
                    valores = [int(uid), int(iid), fini, f_v, cl(ma), 1]
                    
                    if 'procedencia' in cols_db:
                        campos.append("procedencia"); valores.append(str(val_p))
                    elif 'domicilio' in cols_db:
                        campos.append("domicilio"); valores.append(str(val_p))

                    q_ins = f"INSERT INTO contratos ({', '.join(campos)}) VALUES ({', '.join(['?']*len(campos))})"
                    nid = db_query(q_ins, tuple(valores), commit=True)

                    if nid:
                        # B. DEUDAS
                        db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, pagado) VALUES (?, 'Alquiler', ?, 0)", (nid, cl(ma)), commit=True)
                        db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, pagado) VALUES (?, 'Depósito', ?, 0)", (nid, cl(md)), commit=True)

                        # C. PDF (Blindado y con Dirección Real)
                        try:
                            # --- EL ARREGLO ESTÁ AQUÍ ---
                            # Buscamos la dirección real del bloque que corresponde a este inmueble
                            df_dir_real = db_query("SELECT direccion FROM bloques WHERE id = ?", (int(s_u['id_bloque']),))
                            
                            # Creamos una copia de s_u para el PDF y le inyectamos la dirección
                            s_u_pdf = s_u.copy()
                            if df_dir_real is not None and not df_dir_real.empty:
                                s_u_pdf['direccion'] = df_dir_real.iloc[0]['direccion']
                            
                            # Preparamos los datos del inquilino como ya hacíamos
                            s_i_pdf = pd.Series({**s_i.to_dict(), 'direccion': val_p, 'procedencia': val_p})
                            
                            # Llamamos al PDF usando 's_u_pdf' (que ahora sí tiene la calle)
                            pdf_bytes = generar_pdf_v5(s_u_pdf, s_i_pdf, fini, ma, md, mc, uso_sel)
                            # ----------------------------

                            # Guardamos en Session State de forma segura
                            st.session_state['pdf_f'] = pdf_bytes
                            st.session_state['id_f'] = nid
                            st.success(f"✅ ¡Éxito! Contrato #{nid} registrado como {uso_sel}.")
                        except Exception as e_pdf:
                            st.error(f"⚠️ Se grabó el contrato #{nid}, pero falló el archivo PDF: {e_pdf}")
                    else:
                        st.error("❌ La base de datos rechazó el registro. Por favor, revise los logs de la DB.")
                except Exception as e:
                    st.error(f"❌ Error Crítico: {e}")

    # --- D. BOTÓN DE DESCARGA SEGURO (Solo si hay datos válidos) ---
    if 'pdf_f' in st.session_state and st.session_state['pdf_f'] is not None:
        st.write("---")
        # Validamos que id_f exista para no romper el label
        cid = st.session_state.get('id_f', 'N/A')
        st.download_button(
            label=f"📥 DESCARGAR CONTRATO PDF #{cid}",
            data=st.session_state['pdf_f'],
            file_name=f"Contrato_{cid}.pdf",
            mime="application/pdf"
        )
        if st.button("Limpiar"):
            del st.session_state['pdf_f']
            st.rerun()



# ==========================================
# 3. COBRANZAS (V.13.1 - NOMBRE DINÁMICO)
# ==========================================
elif menu == "💰 Cobranzas":
    st.header("Gestión de Cobranzas y Pagos")

    # BLOQUE POST-PAGO
    if st.session_state.get('pago_exitoso'):
        st.success("✅ Pago registrado con éxito.")
        c_pdf, c_res = st.columns(2)
        if 'pdf_cobr' in st.session_state and st.session_state['pdf_cobr']:
            # Recuperamos el nombre dinámico guardado en el State
            nombre_final = st.session_state.get('nombre_archivo_pdf', f"Recibo_{date.today()}.pdf")
            
            c_pdf.download_button(
                label="📥 DESCARGAR RECIBO PDF",
                data=st.session_state['pdf_cobr'],
                file_name=nombre_final,
                mime="application/pdf",
                use_container_width=True
            )
        if c_res.button("🔄 Nueva Cobranza (Limpiar)", use_container_width=True):
            st.session_state['pago_exitoso'] = False
            st.session_state.pop('pdf_cobr', None)
            st.session_state.pop('nombre_archivo_pdf', None)
            st.rerun()
        st.stop()

    # CONSULTA DE DEUDAS
    deu_pend = db_query("""
        SELECT d.id as id_deuda, inq.nombre as Inquilino,
               b.nombre || ' - ' || i.tipo as Referencia,
               d.concepto as Concepto,
               d.monto_debe - COALESCE(d.monto_pago, 0) as Saldo_Pendiente
        FROM deudas d
        JOIN contratos c ON d.id_contrato = c.id
        JOIN inmuebles i ON c.id_inmueble = i.id
        JOIN bloques b ON i.id_bloque = b.id
        JOIN inquilinos inq ON c.id_inquilino = inq.id
        WHERE d.pagado = 0 ORDER BY inq.nombre
    """)

    if deu_pend is not None and not deu_pend.empty:
        st.subheader("Selección de Deudas")

        indices_sel = st.multiselect(
            "Seleccionar deudas a cobrar:",
            deu_pend.index.tolist(),
            format_func=lambda x: f"{deu_pend.loc[x,'Inquilino']} | {deu_pend.loc[x,'Concepto']} | ${deu_pend.loc[x,'Saldo_Pendiente']:,.0f}",
            key="cobr_indices"
        )

        total_marcado = float(deu_pend.loc[indices_sel, 'Saldo_Pendiente'].sum()) if indices_sel else 0.0

        st.markdown(f"""
            <div style="background:#f0f2f6;padding:15px;border-radius:10px;border-left:5px solid #D4AF37;margin-bottom:12px;">
                <h3 style="margin:0;color:#1A1A1A;">
                    TOTAL SELECCIONADO: <span style="color:#D4AF37;">$ {total_marcado:,.0f}</span>
                </h3>
            </div>
        """, unsafe_allow_html=True)

        with st.form("f_cobranza_v131"):
            c1, c2 = st.columns(2)
            f_pago = c1.date_input("Fecha de cobro", date.today())
            m_r = c2.number_input("Monto REAL recibido ($):", min_value=0.0, value=total_marcado, step=100.0, format="%.0f")
            btn = st.form_submit_button("✅ REGISTRAR Y GENERAR RECIBO", use_container_width=True)

        if btn:
            if not indices_sel:
                st.error("Debe seleccionar al menos una deuda.")
            elif m_r <= 0:
                st.error("El monto debe ser mayor a cero.")
            else:
                try:
                    saldo_a = m_r
                    df_filas = deu_pend.loc[indices_sel].copy() # Esta es tu variable de origen
                    detalles_pdf = []

                    for _, fila in df_filas.iterrows():
                        if saldo_a <= 0: break
                        p = float(fila['Saldo_Pendiente'])
                        m_p = p if saldo_a >= p else saldo_a
                        pagado_flag = 1 if saldo_a >= p else 0
                        db_query("UPDATE deudas SET monto_pago = COALESCE(monto_pago,0) + %s, pagado = %s, fecha_pago = %s WHERE id = %s",
                                (m_p, pagado_flag, f_pago.strftime('%Y-%m-%d'), fila['id_deuda']), commit=True)
                        saldo_a -= m_p
                        estado_txt = "Cancelado" if pagado_flag else "Pago Parcial"
                        detalles_pdf.append(f"{fila['Concepto']} - {fila['Referencia']}: ${m_p:,.0f} ({estado_txt})")

                    # --- CONSTRUCCIÓN DEL PDF ---
                    pdf = PDFRecibo()
                    pdf.add_page()
                    pdf.set_font('Arial', 'B', 14)
                    pdf.cell(0, 10, "COMPROBANTE DE PAGO", ln=True, align='C')
                    pdf.ln(5)
                    pdf.set_font('Arial', '', 11)
                    pdf.cell(0, 8, f"Inquilino: {df_filas.iloc[0]['Inquilino']}", ln=True)
                    pdf.cell(0, 8, f"Fecha: {f_pago.strftime('%d/%m/%Y')}", ln=True)
                    pdf.cell(0, 8, "Inmobiliaria: NL PROPIEDADES  |  CUIT: 30-71884850-0", ln=True)
                    pdf.ln(3)
                    pdf.set_font('Arial', 'B', 12)
                    pdf.cell(0, 10, f"TOTAL RECIBIDO: $ {m_r:,.0f}", ln=True)
                    pdf.ln(3)
                    pdf.set_font('Arial', '', 10)
                    for det in detalles_pdf:
                        det_safe = det.encode('latin-1', 'replace').decode('latin-1')
                        pdf.cell(0, 7, f"  > {det_safe}", ln=True)
                    pdf.ln(20)
                    pdf.cell(60, 0, '', 'T', 0, 'C')
                    pdf.ln(3)
                    pdf.set_font('Arial', 'B', 10)
                    pdf.cell(60, 5, "NL INMOBILIARIA", 0, 1, 'C')

                    # Generación de Bytes del PDF
                    raw = pdf.output(dest='S')
                    pdf_bytes = bytes(raw) if isinstance(raw, (bytes, bytearray)) else raw.encode('latin-1')

                    # NOMBRE DINÁMICO: Inquilino + Fecha + Concepto
                    inquilino_n = str(df_filas.iloc[0]['inquilino']).replace(" ", "_")
                    conceptos_str = "-".join(list(df_filas['concepto'].unique())).replace(" ", "_")
                    fecha_str = f_pago.strftime('%Y%m%d')
        
                    st.session_state['nombre_archivo_pdf'] = f"Recibo_{inquilino_n}_{fecha_str}_{conceptos_str}.pdf"
                    st.session_state['pdf_cobr'] = pdf_bytes
                    st.session_state['pago_exitoso'] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar el cobro: {e}")

    # ZONA DE CORRECCIÓN (indentación correcta, al mismo nivel)
    st.write("---")
    with st.expander("🗑️ Zona de Corrección: Eliminar Deuda Errónea"):
        st.info("Use esta opción solo para borrar deudas generadas por error. No la use para registrar cobros.")
        df_pendientes = db_query("""
            SELECT d.id, inq.nombre || ' - ' || d.concepto as Ref
            FROM deudas d
            JOIN contratos c ON d.id_contrato = c.id
            JOIN inquilinos inq ON c.id_inquilino = inq.id
            WHERE d.pagado = 0
        """)
        if df_pendientes is not None and not df_pendientes.empty:
            sel_deuda_borrar = st.selectbox(
                "Seleccione la deuda a ELIMINAR PERMANENTEMENTE:",
                df_pendientes['id'].tolist(),
                format_func=lambda x: df_pendientes[df_pendientes['id']==x]['Ref'].values[0]
            )
            confirmar_borrado = st.checkbox("Confirmo que deseo eliminar este registro permanentemente.")
            if st.button("❌ ELIMINAR REGISTRO"):
                if confirmar_borrado:
                    db_query("DELETE FROM deudas WHERE id=?", (sel_deuda_borrar,), commit=True)
                    st.success("Registro eliminado de la base de datos.")
                    st.rerun()
                else:
                    st.warning("Debe marcar el cuadro de confirmación para proceder.")
        else:
            st.write("No hay deudas pendientes registradas.")        
        
# ==========================================
# --- SECCIÓN MOROSOS CORREGIDA ---
elif menu == "🚨 Morosos":

    st.subheader("Estado de Morosidad")

    query_morosos = """
        SELECT inq.nombre as Inquilino, d.monto_debe as Deuda
        FROM deudas d 
        JOIN contratos c ON d.id_contrato = c.id 
        JOIN inquilinos inq ON c.id_inquilino = inq.id 
        WHERE d.pagado = 0
    """
    df_morosos = db_query(query_morosos)

    if df_morosos is not None and not df_morosos.empty:
        # 1. Calculamos el Total Numérico antes de formatear
        total_deuda_neta = df_morosos['Deuda'].sum()
    
        # 2. Preparamos la visualización (Copia para no romper el original)
        df_morosos_view = df_morosos.copy()
    
        # 3. Aplicamos el formato sin decimales y con punto de miles
        df_morosos_view['Deuda'] = df_morosos_view['Deuda'].apply(f_m)
    
        # 4. Mostramos la tabla con los nombres de columna solicitados
        st.dataframe(df_morosos_view, use_container_width=True, hide_index=True)
    
        # --- 5. TOTALIZADOR RESALTADO ---
        st.write("---")
        c_tot1, c_tot2 = st.columns([2, 1])
        c_tot1.markdown("### TOTAL DEUDA EN CALLE:")
        # Usamos f_m para que el total también sea consistente (sin decimales)
        c_tot2.subheader(f"$ {f_m(total_deuda_neta)}")
    
    else:
        st.success("✅ ¡Excelente! No existen deudas pendientes de cobro.")


# ==========================================
# 4. CONTROL DE CAJA (V.11.2 - INDEPENDIENTE)
# ==========================================
elif menu == "📊 Caja":
    st.header("Historial de Ingresos y Control de Caja")

    # 1. FILTROS DE TIEMPO
    c1, c2 = st.columns([2, 1])
    with c1:
        filtro_caja = st.radio(
            "Visualizar ingresos de:",
            ["Hoy", "Este Mes", "Este Año", "Total Histórico"],
            horizontal=True
        )

    # Lógica de fechas — compatible con PostgreSQL (TO_CHAR)
    hoy      = date.today()
    hoy_str  = hoy.strftime('%Y-%m-%d')
    mes_str  = hoy.strftime('%m')
    anio_str = hoy.strftime('%Y')

    if filtro_caja == "Hoy":
        condicion = "d.fecha_pago::date = %s"
        params    = (hoy_str,)
    elif filtro_caja == "Este Mes":
        condicion = "TO_CHAR(d.fecha_pago, 'MM') = %s AND TO_CHAR(d.fecha_pago, 'YYYY') = %s"
        params    = (mes_str, anio_str)
    elif filtro_caja == "Este Año":
        condicion = "TO_CHAR(d.fecha_pago, 'YYYY') = %s"
        params    = (anio_str,)
    else:
        condicion = "1=1"
        params    = ()

    # 2. CONSULTA — COALESCE (Postgres), alias sin corchetes
    query_caja = f"""
        SELECT
            d.id                              AS ID_Reg,
            inq.nombre                        AS Inquilino,
            b.nombre || ' - ' || i.tipo       AS Unidad,
            d.concepto                        AS Concepto,
            COALESCE(d.monto_pago, 0)         AS Importe,
            d.fecha_pago                      AS Fecha
        FROM deudas d
        JOIN contratos c   ON d.id_contrato  = c.id
        JOIN inmuebles i   ON c.id_inmueble  = i.id
        JOIN bloques b     ON i.id_bloque    = b.id
        JOIN inquilinos inq ON c.id_inquilino = inq.id
        WHERE COALESCE(d.monto_pago, 0) > 0
          AND d.fecha_pago IS NOT NULL
          AND {condicion}
        ORDER BY d.fecha_pago DESC
    """
    # La query ya tiene %s, pasamos params directo (sin conversión ?)
    df_caja = db_query(query_caja, params if params else None)

    if df_caja is not None and not df_caja.empty:
        # 3. MÉTRICAS Y EXPORTACIÓN
        total_recaudado = df_caja['Importe'].sum()

        m1, m2 = st.columns([2, 1])
        m1.metric(f"💰 TOTAL RECAUDADO ({filtro_caja})", f"$ {f_m(total_recaudado)}")

        output_excel = io.BytesIO()
        with pd.ExcelWriter(output_excel, engine='xlsxwriter') as writer:
            df_caja.to_excel(writer, sheet_name='Caja', index=False)

        m2.write(" ")
        m2.download_button(
            label="📥 Exportar Excel",
            data=output_excel.getvalue(),
            file_name=f"Caja_{filtro_caja}_{hoy}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.write("---")

        # 4. VISUALIZACIÓN sin la columna ID interna
        st.dataframe(df_caja.drop(columns=['ID_Reg']), use_container_width=True, hide_index=True)

        # 5. ANULAR PAGO
        with st.expander("🛠️ Corregir error en Caja (Anular Pago)"):
            st.warning("Al anular un registro, la deuda volverá a figurar como PENDIENTE.")
            id_borrar = st.selectbox("Seleccione el ID de registro a anular", df_caja['ID_Reg'].tolist())
            if st.button("❌ ANULAR PAGO"):
                db_query(
                    "UPDATE deudas SET pagado=0, monto_pago=0, fecha_pago=NULL WHERE id=?",
                    (id_borrar,), commit=True
                )
                st.success(f"Registro {id_borrar} anulado. La deuda vuelve a estar pendiente.")
                st.rerun()
    else:
        st.info(f"Sin movimientos registrados para el período: {filtro_caja}")

        
# ==========================================
# 6. CARGAS (V.8.6 - EDICIÓN Y BAJA RESTAURADAS)
# ==========================================
elif menu == "⚙️ Carga":
    st.header("Administración de Base de Datos")
    
    t1, t2, t3, t4, t5, t6, t7 = st.tabs([
        "🏢 Inmuebles", "🏠 Unidades", "👤 Inquilinos", 
        "📋 Contratos", "💾 Backup", "📋 Alquilados", "⚙️ Generación Mensual"
    ])

    # --- 1. INMUEBLES ---
    with t1:
        st.subheader("Edificios y Complejos")
        df_inm = db_query("SELECT id, nombre, direccion, barrio, localidad FROM bloques")
        
        with st.expander("➕ Cargar Nuevo Inmueble"):
            with st.form("f_inm_alta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n = c1.text_input("Nombre del Edificio")
                d = c1.text_input("Dirección")
                b = c2.text_input("Barrio")
                l = c2.text_input("Localidad")
                if st.form_submit_button("Guardar"):
                    db_query("INSERT INTO bloques (nombre, direccion, barrio, localidad) VALUES (?,?,?,?)", (n, d, b, l), commit=True)
                    st.rerun()
        
        if df_inm is not None and not df_inm.empty:
            st.dataframe(df_inm.drop(columns=['id']), use_container_width=True, hide_index=True)
            st.write("---")
            # SECCIÓN EDICIÓN/BORRADO
            sel_inm_nom = st.selectbox("Seleccione Inmueble para gestionar", df_inm['nombre'].tolist())
            dat_inm = df_inm[df_inm['nombre'] == sel_inm_nom].iloc[0]
            
            with st.form("f_inm_edit"):
                c1, c2 = st.columns(2)
                en_n = c1.text_input("Nombre", dat_inm['nombre'])
                en_d = c1.text_input("Dirección", dat_inm['direccion'])
                en_b = c2.text_input("Barrio", dat_inm['barrio'])
                en_l = c2.text_input("Localidad", dat_inm['localidad'])
                
                col_b1, col_b2 = st.columns(2)
                if col_b1.form_submit_button("💾 Actualizar Inmueble"):
                    db_query("UPDATE bloques SET nombre=?, direccion=?, barrio=?, localidad=? WHERE id=?", (en_n, en_d, en_b, en_l, int(dat_inm['id'])), commit=True)
                    st.rerun()
                if col_b2.form_submit_button("🗑️ ELIMINAR"):
                    db_query(f"DELETE FROM bloques WHERE id={int(dat_inm['id'])}", commit=True)
                    st.rerun()

    # --- 2. UNIDADES ---
    with t2:
        st.subheader("Gestión de Unidades")
        df_b_ref = db_query("SELECT id, nombre FROM bloques")
        df_uni = db_query("""SELECT i.id, b.nombre as Inmueble, i.tipo as Unidad, 
                             i.precio_alquiler as Alquiler, i.costo_contrato as Contrato, 
                             i.deposito_base as Deposito, i.id_bloque
                             FROM inmuebles i JOIN bloques b ON i.id_bloque = b.id""")

        if df_b_ref is not None and not df_b_ref.empty:
            with st.expander("➕ Cargar Nueva Unidad"):
                with st.form("f_u_alta", clear_on_submit=True):
                    bid = st.selectbox("Inmueble", df_b_ref['id'], format_func=lambda x: df_b_ref[df_b_ref['id']==x]['nombre'].values[0])
                    tipo = st.text_input("Descripción Unidad")
                    c1, c2, c3 = st.columns(3)
                    p1 = c1.text_input("Alquiler")
                    p2 = c2.text_input("Contrato")
                    p3 = c3.text_input("Deposito")
                    if st.form_submit_button("Crear"):
                        db_query("INSERT INTO inmuebles (id_bloque, tipo, precio_alquiler, costo_contrato, deposito_base) VALUES (?,?,?,?,?)", (bid, tipo, cl(p1), cl(p2), cl(p3)), commit=True)
                        st.rerun()
            
            if df_uni is not None and not df_uni.empty:
                df_u_show = df_uni.drop(columns=['id', 'id_bloque']).copy()
                for col in ['Alquiler', 'Contrato', 'Deposito']: df_u_show[col] = df_u_show[col].apply(f_m)
                st.dataframe(df_u_show, use_container_width=True, hide_index=True)
                
                st.write("---")
                sel_u_ref = st.selectbox("Seleccione Unidad para gestionar", df_uni.index.tolist(), format_func=lambda x: f"{df_uni.loc[x, 'Inmueble']} - {df_uni.loc[x, 'Unidad']}")
                dat_u = df_uni.loc[sel_u_ref]
                
                with st.form("f_u_edit"):
                    c1, c2, c3 = st.columns(3)
                    eu_t = st.text_input("Descripción", dat_u['Unidad'])
                    eu_a = c1.text_input("Alquiler", f_m(dat_u['Alquiler']))
                    eu_c = c2.text_input("Contrato", f_m(dat_u['Contrato']))
                    eu_d = c3.text_input("Deposito", f_m(dat_u['Deposito']))
                    
                    cb1, cb2 = st.columns(2)
                    if cb1.form_submit_button("💾 Actualizar Unidad"):
                        db_query("UPDATE inmuebles SET tipo=?, precio_alquiler=?, costo_contrato=?, deposito_base=? WHERE id=?", (eu_t, cl(eu_a), cl(eu_c), cl(eu_d), int(dat_u['id'])), commit=True)
                        st.rerun()
                    if cb2.form_submit_button("🗑️ ELIMINAR"):
                        db_query(f"DELETE FROM inmuebles WHERE id={int(dat_u['id'])}", commit=True)
                        st.rerun()

    # --- 3. INQUILINOS --- (Se mantiene Domicilio y Edición)
    with t3:
        st.subheader("Registro de Inquilinos")
        df_inq = db_query("SELECT id, nombre, dni, celular, procedencia, grupo, emergencia FROM inquilinos")
        
        with st.expander("➕ Cargar Nuevo Inquilino"):
            with st.form("f_inq_alta", clear_on_submit=True):
                c1, c2 = st.columns(2)
                n = c1.text_input("Nombre y Apellido")
                dni = c1.text_input("DNI / CUIT")
                cel = c1.text_input("WhatsApp")
                dom = c2.text_input("Domicilio")
                gru = c2.text_input("Grupo")
                eme = c2.text_input("Emergencia")
                if st.form_submit_button("Guardar Inquilino"):
                    db_query("INSERT INTO inquilinos (nombre, dni, celular, procedencia, grupo, emergencia) VALUES (?,?,?,?,?,?)", (n, dni, cel, dom, gru, eme), commit=True)
                    st.rerun()
        
        if df_inq is not None and not df_inq.empty:
            # 1. Renombramos y quitamos el ID
            df_inq_v = df_inq.rename(columns={'procedencia': 'Domicilio'}).drop(columns=['id'])
            
            # 2. ESTA ES LA LÍNEA MÁGICA: Pone la primera letra en mayúscula a todas las columnas
            df_inq_v.columns = [c.capitalize() for c in df_inq_v.columns]
            
            # 3. Mostramos el DataFrame
            st.dataframe(df_inq_v, use_container_width=True, hide_index=True)            
            st.write("---")
            sel_inq_nom = st.selectbox("Seleccione Inquilino para gestionar", df_inq['nombre'].tolist())
            i_dat = df_inq[df_inq['nombre'] == sel_inq_nom].iloc[0]
            
            with st.form("f_inq_edit"):
                c1, c2 = st.columns(2)
                en_n = c1.text_input("Nombre", i_dat['nombre'])
                en_d = c1.text_input("DNI", i_dat['dni'])
                en_c = c1.text_input("WhatsApp", i_dat['celular'])
                en_p = c2.text_input("Domicilio", i_dat['procedencia'])
                en_g = c2.text_input("Grupo", i_dat['grupo'])
                en_e = c2.text_input("Emergencia", i_dat['emergencia'])
                
                col_i1, col_i2 = st.columns(2)
                if col_i1.form_submit_button("💾 Actualizar"):
                    db_query("UPDATE inquilinos SET nombre=?, dni=?, celular=?, procedencia=?, grupo=?, emergencia=? WHERE id=?", (en_n, en_d, en_c, en_p, en_g, en_e, int(i_dat['id'])), commit=True)
                    st.rerun()
                if col_i2.form_submit_button("🗑️ BORRAR"):
                    db_query(f"DELETE FROM inquilinos WHERE id={int(i_dat['id'])}", commit=True)
                    st.rerun()


# --- 4. CONTRATOS (V.9.5 - RENOVACIÓN CON CONTINUIDAD Y PDF) ---
    with t4:
        st.subheader("Gestión de Contratos Vigentes")
        
        query_cont = """
            SELECT 
                c.id as ID_Contrato, b.nombre as Inmueble, i.tipo as Unidad, 
                inq.nombre as Inquilino, c.fecha_inicio as Inicio, c.fecha_fin as Fin,
                c.monto_alquiler as [Alq_Actual], i.precio_alquiler as Alq_Maestro,
                i.costo_contrato as Con_Maestro, i.deposito_base as Dep_Maestro,
                c.id_inmueble, c.id_inquilino
            FROM contratos c 
            INNER JOIN inmuebles i ON c.id_inmueble = i.id 
            INNER JOIN bloques b ON i.id_bloque = b.id 
            INNER JOIN inquilinos inq ON c.id_inquilino = inq.id 
            WHERE c.activo = 1
        """
        df_cont = db_query(query_cont)
        
        if df_cont is not None and not df_cont.empty:
            df_display = df_cont[['ID_Contrato', 'Inmueble', 'Unidad', 'Inquilino', 'Inicio', 'Fin', 'Alq_Actual']].copy()
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
            st.write("---")
            c1, c2 = st.columns(2)
            sel_c_id = c1.selectbox("Seleccione ID de Contrato", df_cont['ID_Contrato'].tolist())
            row_sel = df_cont[df_cont['ID_Contrato'] == sel_c_id].iloc[0]
            
            if c1.button("🚨 FINALIZAR CONTRATO"):
                db_query(f"UPDATE contratos SET activo=0 WHERE id={sel_c_id}", commit=True)
                st.rerun()
            
            with c2:
                st.markdown("**🔄 Renovar con Continuidad**")
                meses_r = st.number_input("Meses a renovar", min_value=1, value=6, key="r_meses")
                
                if st.button("🚀 EJECUTAR RENOVACIÓN Y PDF"):
                    try:
                        # 1. LÓGICA DE FECHAS: Continuidad absoluta
                        # El nuevo inicia el día después del fin del anterior
                        f_fin_anterior = pd.to_datetime(row_sel['Fin']).date()
                        f_ini_n = f_fin_anterior + timedelta(days=1)
                        f_fin_n = f_ini_n + timedelta(days=meses_r * 30)
                        
                        # 2. Transacción: Baja del viejo y Alta del nuevo
                        db_query(f"UPDATE contratos SET activo=0 WHERE id={sel_c_id}", commit=True)
                        
                        nuevo_id = db_query("""
                            INSERT INTO contratos (id_inmueble, id_inquilino, fecha_inicio, fecha_fin, monto_alquiler, activo) 
                            VALUES (?,?,?,?,?,1)
                        """, (int(row_sel['id_inmueble']), int(row_sel['id_inquilino']), f_ini_n, f_fin_n, int(row_sel['Alq_Maestro'])), commit=True)
                        
                        # 3. Deudas automáticas
                        db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, monto_pago, pagado) VALUES (?, 'Alquiler Mes 1 (Renov)', ?, 0, 0)", (nuevo_id, int(row_sel['Alq_Maestro'])), commit=True)
                        db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, monto_pago, pagado) VALUES (?, 'Depósito (Renov)', ?, 0, 0)", (nuevo_id, int(row_sel['Dep_Maestro'])), commit=True)
                        db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, monto_pago, pagado) VALUES (?, 'Gasto Contrato (Renov)', ?, 0, 0)", (nuevo_id, int(row_sel['Con_Maestro'])), commit=True)
                        
                        # 4. GENERACIÓN DE PDF INMEDIATA
                        # Esta consulta garantiza que traemos la dirección desde la tabla de edificios (bloques)
                        u_data_full = db_query("""
                            SELECT i.*, b.direccion, b.nombre as nombre_edificio
                            FROM inmuebles i 
                            JOIN bloques b ON i.id_bloque = b.id 
                            WHERE i.id = ?
                        """, (uid,)).iloc[0]                        

                        #pdf_bytes = generar_pdf_v5(u_data, inq_data, f_ini_n, f_m(row_sel['Alq_Maestro']), f_m(row_sel['Dep_Maestro']), f_m(row_sel['Con_Maestro']))
                        # Ahora llamamos a la función usando 'u_data_full' en lugar de 's_u'
                        pdf_out = generar_pdf_v5(u_data_full, s_i, fini, ma, md, mc)

                        
                        # Guardamos en session_state para que el botón de descarga aparezca
                        st.session_state['pdf_ready'] = bytes(pdf_bytes)
                        st.session_state['cid_last'] = nuevo_id
                        
                        st.success(f"Renovado. Nuevo Contrato: {nuevo_id} (Inicia: {f_ini_n})")
                        st.rerun() # Recargamos para actualizar la tabla y mostrar el PDF
                        
                    except Exception as e:
                        st.error(f"Error en renovación: {e}")

        # Sección de descarga (se muestra si existe un PDF recién generado)
        if 'pdf_ready' in st.session_state:
            st.write("---")
            st.info(f"📄 PDF del Nuevo Contrato #{st.session_state.get('cid_last')} listo para descargar")
            st.download_button("📥 DESCARGAR CONTRATO RENOVADO", st.session_state['pdf_ready'], f"Renovacion_{st.session_state['cid_last']}.pdf", "application/pdf")
            if st.button("Limpiar Notificación"):
                del st.session_state['pdf_ready']
                st.rerun()



    # --- 5. BACKUP & RESTORE (V.13.0 - BOTÓN DE DESCARGA FIJO) ---
    with t5:
        st.subheader("💾 Centro de Datos y Seguridad")
        c_exp, c_imp, c_res = st.columns(3)
        
        with c_exp:
            st.write("**Exportar Datos**")
            # Paso 1: Generar el archivo
            if st.button("📂 Preparar Archivo de Respaldo"):
                try:
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        # Tablas a exportar
                        for tabla, hoja in [('bloques','Inmuebles'), ('inmuebles','Unidades'), 
                                           ('inquilinos','Inquilinos'), ('contratos','Contratos'), 
                                           ('deudas','Deudas'),
                                           # --- LOTES (Asegurate que estas 5 estén aquí) ---
                                           ('desarrollos', 'Loteos_Desarrollos'),
                                           ('lotes', 'Lotes_Inventario'),
                                           ('compradores', 'Lotes_Compradores'),
                                           ('ventas_lotes', 'Lotes_Ventas'),
                                           ('cuotas_lotes', 'Lotes_Cuotas') ]:
                            df_tmp = db_query(f"SELECT * FROM {tabla}")
                            if df_tmp is not None:
                                df_tmp.to_excel(writer, sheet_name=hoja, index=False)
                    
                    # Guardamos el binario en el estado de la sesión
                    st.session_state['archivo_backup'] = output.getvalue()
                    st.success("✅ Archivo preparado con éxito.")
                except Exception as e:
                    st.error(f"Error al preparar backup: {e}")

            # Paso 2: Mostrar el botón de descarga si el archivo existe en memoria
            if 'archivo_backup' in st.session_state:
                st.download_button(
                    label="📥 DESCARGAR EXCEL",
                    data=st.session_state['archivo_backup'],
                    file_name=f"Backup_Inmobiliaria_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="btn_descarga_final"
                )
                if st.button("Limpiar descarga", key="clear_bak"):
                    del st.session_state['archivo_backup']
                    st.rerun()


        with c_imp:
            st.write("**Restaurar Datos**")
            archivo_subido = st.file_uploader("Subir backup (.xlsx)", type=["xlsx"], key="restore_uploader")
            if archivo_subido:
                if st.button("🚀 Ejecutar Restauración"):
                    try:
                        engine = obtener_engine()
                        dfs = pd.read_excel(archivo_subido, sheet_name=None)
                        mapping = {
                            'Inmuebles':'bloques', 'Unidades':'inmuebles', 
                            'Inquilinos':'inquilinos', 'Contratos':'contratos', 'Deudas':'deudas',
                            'desarrollos': 'Loteos_Desarrollos', 'lotes':'Lotes_Inventario',
                            'compradores':'Lotes_Compradores', 'ventas_lotes':'Lotes_Ventas',
                            'cuotas_lotes':'Lotes_Cuotas'
                        }
                        
                        with engine.begin() as conn:
                            for hoja, tabla in mapping.items():
                                if hoja in dfs:
                                    # Limpieza profesional de tabla
                                    conn.execute(text(f'TRUNCATE TABLE "{tabla}" RESTART IDENTITY CASCADE;'))
                                    # Carga masiva
                                    dfs[hoja].to_sql(tabla, engine, if_exists='append', index=False, method='multi')
                        
                        st.success("✅ ¡Sistema restaurado en Supabase!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error en restauración: {e}")

        with c_res:
            st.write("**Limpiar Sistema**")
            if st.button("🗑️ Vaciar todas las Tablas"):
                try:
                    conn = conectar_db()
                    if conn:
                        cur = conn.cursor()
                        tablas = ['bloques', 'inmuebles', 'inquilinos', 'contratos', 'deudas', 
                                 'Loteos_Desarrollos', 'Lotes_Inventario', 'Lotes_Compradores', 
                                 'Lotes_Ventas', 'Lotes_Cuotas']
                        for t in tablas:
                            cur.execute(f'TRUNCATE TABLE "{t}" RESTART IDENTITY CASCADE;')
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("✅ Base de datos vaciada.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error al limpiar: {e}")
            

    # --- 6. LISTADO DE ALQUILADOS ---
    with t6:
        st.subheader("📋 Ocupación Actual")
        df_alq = db_query("""
            SELECT b.nombre as Inmueble, i.tipo as Unidad, inq.nombre as Inquilino, inq.procedencia as Domicilio, inq.celular as [WhatsApp],
                   COALESCE((SELECT SUM(monto_debe - monto_pago) FROM deudas WHERE id_contrato = c.id AND pagado = 0), 0) as Saldo
            FROM contratos c JOIN inmuebles i ON c.id_inmueble = i.id JOIN bloques b ON i.id_bloque = b.id JOIN inquilinos inq ON c.id_inquilino = inq.id
            WHERE c.activo = 1 ORDER BY b.nombre
        """)
        if df_alq is not None and not df_alq.empty:
            df_v = df_alq.copy(); df_v['Saldo'] = df_v['Saldo'].apply(lambda x: f"🔴 ${f_m(x)}" if x > 0 else "🟢 Al día")
            st.dataframe(df_v, use_container_width=True, hide_index=True)
            st.metric("Deuda Total en Calle", f"$ {f_m(df_alq['Saldo'].sum())}")

    # --- 7. GENERACIÓN MENSUAL ---
    with t7:
        st.subheader("⚙️ Generación de Deuda")
        with st.form("f_gen_mas"):
            mes = st.selectbox("Mes", ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"])
            anio = st.number_input("Año", value=2026)
            if st.form_submit_button("Ejecutar Generación"):
                conts = db_query("SELECT id, monto_alquiler FROM contratos WHERE activo=1")
                for _, c in conts.iterrows():
                    conc = f"Alquiler {mes} {anio}"
                    if db_query("SELECT id FROM deudas WHERE id_contrato=? AND concepto=?", (int(c['id']), conc)).empty:
                        db_query("INSERT INTO deudas (id_contrato, concepto, monto_debe, monto_pago, pagado) VALUES (?,?,?,0,0)", (int(c['id']), conc, int(c['monto_alquiler'])), commit=True)
                st.success("Cargos generados.")

# ==========================================
# 7. GESTIÓN DE LOTES (V.2.6 - AJUSTES DE PRECISIÓN)
# ==========================================
elif menu == "🌳 Lotes":
    st.header("Gestión y Comercialización de Lotes (U$D)")
    
    if not os.path.exists("fotos_lotes"):
        os.makedirs("fotos_lotes")

    t_l1, t_l2, t_l3, t_l4, t_l5 = st.tabs([
        "🏗️ Nombre del Loteo", "📏 Inventario Lotes", "👤 Compradores", "🤝 Ventas", "💰 Cuotas y Cobros"
    ])

    # --- 1. NOMBRE DEL LOTEO (EX DESARROLLO) ---
    with t_l1:
        st.subheader("Configuración de Nombres de Loteos")
        with st.form("f_loteo_nuevo", clear_on_submit=True):
            n_name = st.text_input("Nombre del Loteo (Ej: Los Olivos)")
            n_ubica = st.text_input("Ubicación / Ruta")
            n_local = st.text_input("Localidad")
            if st.form_submit_button("💾 GRABAR NOMBRE DE LOTEO"):
                if n_name:
                    db_query("INSERT INTO desarrollos (nombre, ubicacion, localidad) VALUES (?,?,?)", 
                             (n_name, n_ubica, n_local), commit=True)
                    st.success("✅ Nombre de loteo guardado.")
                    st.rerun()

        st.write("---")
        df_loteos = db_query("SELECT id as ID, nombre as [Nombre del Loteo], ubicacion as [Ubicación], localidad as Localidad FROM desarrollos")
        if df_loteos is not None and not df_loteos.empty:
            st.table(df_loteos)

    # --- 2. INVENTARIO DE LOTES (CON DECIMALES EN MEDIDAS) ---
    with t_l2:
        st.subheader("📦 Gestión de Inventario")
        df_d_ref = db_query("SELECT id, nombre FROM desarrollos")
        
        if df_d_ref is not None and not df_d_ref.empty:
            with st.expander("📝 Carga de Lote (ID Automático)", expanded=True):
                with st.form("f_lote_v26", clear_on_submit=True):
                    id_d = st.selectbox("NOMBRE DEL LOTEO", df_d_ref['id'], 
                                        format_func=lambda x: df_d_ref[df_d_ref['id']==x]['nombre'].values[0])
                    
                    c1, c2, c3 = st.columns(3)
                    lt = c1.text_input("NRO LOTE")
                    mz = c2.text_input("MANZANA")
                    titular = c3.text_input("TITULAR CEDENTE")
                    
                    f1, f2, f3, f4 = st.columns(4)
                    # AQUÍ PERMITIMOS 2 DECIMALES (step=0.01)
                    m2 = f1.number_input("M2 Totales", min_value=0.0, step=0.01, format="%.2f")
                    fre = f2.number_input("Frente (m)", min_value=0.0, step=0.01, format="%.2f")
                    fon = f3.number_input("Fondo (m)", min_value=0.0, step=0.01, format="%.2f")
                    amojon = f4.selectbox("Amojonamiento", ["NO", "SI"])
                    
                    s1, s2 = st.columns(2)
                    serv = s1.multiselect("Servicios", ["LUZ", "AGUA", "INTERNET", "GAS"])
                    c_amojon = s2.number_input("Costo Amojonamiento", min_value=0, step=1)

                    st.markdown("---")
                    st.markdown("**💰 Propuesta Económica** (Montos sin decimales)")
                    
                    p1, p2 = st.columns([2, 1])
                    p_cont = p1.number_input("Precio Contado", min_value=0, step=1)
                    m_cont = p2.selectbox("Moneda Cont.", ["U$D", "PESOS"], key="m1")
                    
                    e1, e2 = st.columns([2, 1])
                    p_ent = e1.number_input("Entrega pactada", min_value=0, step=1)
                    m_ent = e2.selectbox("Moneda Ent.", ["PESOS", "U$D"], key="m2")
                    
                    q1, q2, q3 = st.columns([1, 2, 1])
                    p_q_n = q1.number_input("Cant. Cuotas", min_value=0, value=12)
                    p_q_v = q2.number_input("Valor Cuota", min_value=0, step=1)
                    m_q = q3.selectbox("Moneda Cuota", ["U$D", "PESOS"], key="m3")
                    
                    obs = st.text_area("Observaciones")
                    fotos = st.file_uploader("Subir Imágenes", accept_multiple_files=True)
                    
                    if st.form_submit_button("💾 GUARDAR REGISTRO"):
                        new_id = db_query("""INSERT INTO lotes 
                            (id_desarrollo, nro_lote, manzana, titular_cedente, metros_cuadrados, frente, fondo, 
                            amojonamiento, costo_amojonamiento, servicios, precio_contado, moneda_contado, 
                            entrega_monto, moneda_entrega, cuotas_monto, moneda_cuotas, cant_cuotas, observaciones) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", 
                            (id_d, lt, mz, titular, m2, fre, fon, amojon, c_amojon, ", ".join(serv), 
                             p_cont, m_cont, p_ent, m_ent, p_q_v, m_q, p_q_n, obs), commit=True)
                        
                        if fotos:
                            for i, foto in enumerate(fotos):
                                with open(f"fotos_lotes/lote_{new_id}_{i}.jpg", "wb") as f:
                                    f.write(foto.getbuffer())
                        st.success(f"✅ Lote guardado con ID: {new_id}")
                        st.rerun()

            # --- TABLA DE INVENTARIO ---
            st.write("---")
            df_lotes = db_query("""
                SELECT l.id as ID, d.nombre as [Nombre del Loteo], l.nro_lote as Lote, l.manzana as Mz, 
                       l.metros_cuadrados as [M2], l.amojonamiento as Amoj, l.estado as Estado
                FROM lotes l JOIN desarrollos d ON l.id_desarrollo = d.id ORDER BY l.id DESC
            """)
            if df_lotes is not None:
                st.dataframe(df_lotes, use_container_width=True, hide_index=True)

                
    # --- 3. GESTIÓN DE COMPRADORES (V.2.7 - ID AUTOMÁTICO Y REFRESCO) ---
    with t_l3:
        st.subheader("👤 Registro de Compradores")

        # 1. Formulario de Alta (Sin campo ID, es automático)
        with st.expander("➕ Registrar Nuevo Comprador", expanded=True):
            with st.form("f_comprador_nuevo", clear_on_submit=True):
                c1, c2 = st.columns(2)
                nombre_c = c1.text_input("Nombre y Apellido / Razón Social")
                dni_c = c1.text_input("DNI / CUIT")
                cel_c = c2.text_input("Teléfono Celular")
                mail_c = c2.text_input("Correo Electrónico")
                domicilio_c = st.text_input("Domicilio Real")
                
                btn_guardar_c = st.form_submit_button("💾 GUARDAR COMPRADOR")
                
                if btn_guardar_c:
                    if nombre_c.strip() == "":
                        st.error("El nombre es obligatorio para el registro.")
                    else:
                        try:
                            # INSERT con ID Automático (NULL en la PK)
                            sql_ins_comp = """
                                INSERT INTO compradores (nombre, dni_cuit, celular, domicilio, email) 
                                VALUES (?, ?, ?, ?, ?)
                            """
                            nuevo_id_c = db_query(sql_ins_comp, 
                                                (nombre_c, dni_c, cel_c, domicilio_c, mail_c), 
                                                commit=True)
                            
                            st.success(f"✅ Comprador registrado con éxito. ID Sistema: {nuevo_id_c}")
                            st.rerun() # Fuerza la actualización de la tabla de abajo
                        except Exception as e:
                            st.error(f"Error al guardar en base de datos: {e}")

        # 2. Listado de Compradores (Siempre visible abajo)
        st.write("---")
        st.subheader("📋 Base de Datos de Compradores")
        
        # Consultamos los datos (Asignamos alias para que la tabla sea legible)
        df_comp_list = db_query("""
            SELECT id as ID, nombre as Nombre, dni_cuit as [DNI/CUIT], 
                   celular as Celular, email as [E-mail] 
            FROM compradores 
            ORDER BY id DESC
        """)
        
        if df_comp_list is not None and not df_comp_list.empty:
            # Mostramos la tabla ocupando todo el ancho
            st.dataframe(df_comp_list, use_container_width=True, hide_index=True)
            
            # Opción de eliminación rápida
            with st.expander("🗑️ Zona de Eliminación"):
                id_eliminar_c = st.number_input("ID de Comprador a borrar", min_value=1, step=1, key="del_comp_id")
                if st.button("❌ ELIMINAR REGISTRO SELECCIONADO", key="btn_del_comp"):
                    db_query(f"DELETE FROM compradores WHERE id={id_eliminar_c}", commit=True)
                    st.warning(f"Registro ID {id_eliminar_c} eliminado.")
                    st.rerun()
        else:
            st.info("Aún no hay compradores registrados en el sistema.")

    # --- 4. GESTIÓN DE VENTAS (V.2.8) ---
    with t_l4:
        st.subheader("🤝 Registrar Venta de Lote")
        
        # Query que combina Loteo + Manzana + Lote para identificar unívocamente
        query_lotes_libres = """
            SELECT l.id, d.nombre || ' - Mz: ' || l.manzana || ' - Lote: ' || l.nro_lote as ref,
                   l.precio_contado, l.entrega_monto, l.cant_cuotas, l.cuotas_monto, l.moneda_cuotas
            FROM lotes l 
            JOIN desarrollos d ON l.id_desarrollo = d.id 
            WHERE l.estado = 'Libre'
        """
        lotes_libres = db_query(query_lotes_libres)
        comps = db_query("SELECT id, nombre FROM compradores")
        
        if lotes_libres is not None and not lotes_libres.empty and comps is not None:
            with st.form("f_venta_lote_v28"):
                # 1. Identificación del Lote y Comprador
                id_l = st.selectbox("Seleccione Lote (Loteo - Mz - Lote)", lotes_libres['id'], 
                                    format_func=lambda x: lotes_libres[lotes_libres['id']==x]['ref'].values[0])
                id_c = st.selectbox("Comprador", comps['id'], 
                                    format_func=lambda x: comps[comps['id']==x]['nombre'].values[0])
                
                # Traemos valores sugeridos del inventario para el lote seleccionado
                sugerido = lotes_libres[lotes_libres['id'] == id_l].iloc[0]
                
                col1, col2 = st.columns(2)
                f_venta = col1.date_input("Fecha de la Venta", value=date.today())
                f_inicio_cuotas = col2.date_input("Mes de 1ra Cuota (Para generar cronograma)", value=date.today())
                
                st.markdown("---")
                c1, c2, c3 = st.columns(3)
                v_total = c1.number_input("Precio Venta Pactado (U$D)", value=int(sugerido['precio_contado']))
                v_entrega = c2.number_input("Entrega Recibida", value=int(sugerido['entrega_monto']))
                v_cant_q = c3.number_input("Cantidad de Cuotas", value=int(sugerido['cant_cuotas']))
                
                v_monto_q = c1.number_input("Monto de cada Cuota", value=int(sugerido['cuotas_monto']))
                v_moneda_q = c2.selectbox("Moneda de la Cuota", ["U$D", "PESOS"], 
                                         index=0 if sugerido['moneda_cuotas'] == 'U$D' else 1)
                
                st.info("💡 Al confirmar, se generará el plan de cuotas automáticamente.")
                
                if st.form_submit_button("🤝 CONFIRMAR VENTA Y GENERAR DEUDA"):
                    # 1. Registrar la Venta
                    v_id = db_query("""INSERT INTO ventas_lotes 
                        (id_lote, id_comprador, fecha_venta, monto_total_usd, entrega_usd, cantidad_cuotas, monto_cuota_usd) 
                        VALUES (?,?,?,?,?,?,?)""", 
                        (id_l, id_c, f_venta, v_total, v_entrega, v_cant_q, v_monto_q), commit=True)
                    
                    # 2. Generar las Cuotas con fecha incremental desde f_inicio_cuotas
                    for i in range(1, v_cant_q + 1):
                        venc = f_inicio_cuotas + timedelta(days=30 * (i-1))
                        db_query("""INSERT INTO cuotas_lotes (id_venta, nro_cuota, monto_usd, fecha_vencimiento, pagado) 
                                 VALUES (?,?,?,?,0)""", (v_id, i, v_monto_q, venc), commit=True)
                    
                    # 3. Marcar lote como Vendido
                    db_query(f"UPDATE lotes SET estado='Vendido' WHERE id={id_l}", commit=True)
                    st.success("Venta realizada y plan de cuotas generado.")
                    st.rerun()

    # --- 5. COBRANZAS, MARCADOR HISTÓRICO Y CONSULTAS (V.2.8) ---
    with t_l5:
        st.subheader("💰 Gestión de Cobranzas y Estado de Cuentas")
        
        sub_tab1, sub_tab2 = st.tabs(["💵 Cobrar / Marcar Pagado", "📊 Consultas y Totales"])
        
        with sub_tab1:
            # Traemos cuotas impagas
            query_q = """
                SELECT cl.id, d.nombre as Loteo, l.manzana, l.nro_lote, co.nombre as Cliente, 
                       cl.nro_cuota, cl.monto_usd, cl.fecha_vencimiento
                FROM cuotas_lotes cl
                JOIN ventas_lotes vl ON cl.id_venta = vl.id
                JOIN lotes l ON vl.id_lote = l.id
                JOIN desarrollos d ON l.id_desarrollo = d.id
                JOIN compradores co ON vl.id_comprador = co.id
                WHERE cl.pagado = 0
            """
            df_q = db_query(query_q)
            
            if df_q is not None and not df_q.empty:
                with st.form("f_cobro_lote"):
                    sel_q = st.selectbox("Seleccione Cuota para operar", df_q['id'].tolist(),
                        format_func=lambda x: f"{df_q[df_q['id']==x]['Cliente'].values[0]} | {df_q[df_q['id']==x]['Loteo'].values[0]} Mz {df_q[df_q['id']==x]['manzana'].values[0]} Lote {df_q[df_q['id']==x]['nro_lote'].values[0]} | Q:{df_q[df_q['id']==x]['nro_cuota'].values[0]} | Vence: {df_q[df_q['id']==x]['fecha_vencimiento'].values[0]}")
                    
                    c_mon = st.number_input("Monto a cobrar (U$D o Pesos según pactado)", value=float(df_q[df_q['id'] == sel_q]['monto_usd'].values[0]))
                    
                    col_b1, col_b2 = st.columns(2)
                    op_cobrar = col_b1.form_submit_button("✅ REGISTRAR PAGO (CAJA)")
                    op_marcar = col_b2.form_submit_button("📁 MARCAR COMO PAGADA (HISTÓRICO)")
                    
                    if op_cobrar or op_marcar:
                        # Si es "marcar", no debería afectar la caja del día si es histórico, 
                        # pero para simplicidad administrativa, ambos marcan pagado=1
                        db_query("UPDATE cuotas_lotes SET pagado=1, monto_pagado_usd=?, fecha_pago=? WHERE id=?", 
                                 (c_mon, date.today(), sel_q), commit=True)
                        st.success("Operación registrada.")
                        st.rerun()
            else:
                st.info("No hay cuotas pendientes de cobro.")

        with sub_tab2:
            st.subheader("🔍 Filtros Avanzados de Cartera")
            
            # --- FILTROS ---
            f_loteos_df = db_query("SELECT nombre FROM desarrollos")
            lista_loteos = ["Todos"] + f_loteos_df['nombre'].tolist() if f_loteos_df is not None else ["Todos"]
            
            c_f1, c_f2, c_f3 = st.columns(3)
            sel_loteo = c_f1.selectbox("Filtrar por Loteo", lista_loteos)
            sel_mz = c_f2.text_input("Manzana (opcional)")
            sel_lt = c_f3.text_input("Lote (opcional)")
            
            c_f4, c_f5, c_f6 = st.columns(3)
            # Filtro de Mes/Año
            meses = ["Todos", "01","02","03","04","05","06","07","08","09","10","11","12"]
            sel_mes = c_f4.selectbox("Mes de Vencimiento", meses)
            sel_anio = c_f5.number_input("Año de Vencimiento", min_value=2020, max_value=2035, value=2026)
            
            # Filtro de Estado Detallado
            sel_estado = c_f6.selectbox("Estado de Cuota", 
                                       ["Todas", "Pagadas", "Impagas (A vencer)", "VENCIDAS (Mora)"])

            # --- CONSTRUCCIÓN DE QUERY DINÁMICA ---
            hoy_str = date.today().strftime('%Y-%m-%d')
            
            q_rep = f"""
                SELECT d.nombre as Loteo, l.manzana as Mz, l.nro_lote as Lote, co.nombre as Cliente,
                       cl.nro_cuota as [Q#], cl.monto_usd as Monto, cl.fecha_vencimiento as Vencimiento,
                       CASE 
                            WHEN cl.pagado = 1 THEN 'PAGADA'
                            WHEN cl.pagado = 0 AND cl.fecha_vencimiento::date < '{hoy_str}'::date THEN 'VENCIDA'
                            ELSE 'A VENCER'
                       END as Estado_Real
                FROM cuotas_lotes cl
                JOIN ventas_lotes vl ON cl.id_venta = vl.id
                JOIN lotes l ON vl.id_lote = l.id
                JOIN desarrollos d ON l.id_desarrollo = d.id
                JOIN compradores co ON vl.id_comprador = co.id
                WHERE 1=1
            """
            
            # Aplicación de filtros lógicos
            if sel_loteo != "Todos": q_rep += f" AND d.nombre = '{sel_loteo}'"
            if sel_mz: q_rep += f" AND l.manzana = '{sel_mz}'"
            if sel_lt: q_rep += f" AND l.nro_lote = '{sel_lt}'"
            
            if sel_mes != "Todos":
                # Formato SQLite para filtrar por mes/año en strings YYYY-MM-DD
                q_rep += f" AND TO_CHAR(cl.fecha_vencimiento, 'MM') = '{sel_mes}'"
                q_rep += f" AND TO_CHAR(cl.fecha_vencimiento, 'YYYY') = '{sel_anio}'"

            # Filtro de estado por lógica de fecha
            if sel_estado == "Pagadas": 
                q_rep += " AND cl.pagado = 1"
            elif sel_estado == "Impagas (A vencer)": 
                q_rep += f" AND cl.pagado = 0 AND cl.fecha_vencimiento::date >= '{hoy_str}'::date"
            elif sel_estado == "VENCIDAS (Mora)": 
                q_rep += f" AND cl.pagado = 0 AND cl.fecha_vencimiento::date < '{hoy_str}'::date"
            
            df_final = db_query(q_rep)
            
            if df_final is not None and not df_final.empty:
                st.write(f"Resultados: {len(df_final)} cuotas encontradas.")
                
                # Visualización
                df_v = df_final.copy()
                df_v['Monto'] = df_v['Monto'].apply(f_m)
                st.dataframe(df_v, use_container_width=True, hide_index=True)
                
                # Totales y Exportación
                total_nro = df_final['Monto'].sum()
                c_res1, c_res2 = st.columns([2,1])
                c_res1.metric("TOTAL FILTRADO", f"U$D / $ {f_m(total_nro)}")
                
                # --- EXPORTAR A EXCEL ---
                output_xlsx = io.BytesIO()
                with pd.ExcelWriter(output_xlsx, engine='xlsxwriter') as writer:
                    df_final.to_excel(writer, index=False, sheet_name='Cobranzas_Filtradas')
                
                c_res2.download_button(
                    label="📥 EXPORTAR A EXCEL",
                    data=output_xlsx.getvalue(),
                    file_name=f"Reporte_Cobranzas_{sel_loteo}_{sel_mes}_{sel_anio}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("No se encontraron registros con los filtros seleccionados.")

# ==========================================
# 1. INVENTARIO (V.6.8 - VISTA LIMPIA)
# ==========================================
elif menu == "🏠 Inventario":
    st.header("Estado de Unidades y Disponibilidad")
    
    query_inv = """
        SELECT 
            b.nombre as Inmueble, 
            i.tipo as Unidad, 
            i.precio_alquiler as Alquiler, 
            i.costo_contrato as Contrato, 
            i.deposito_base as Deposito,
            CASE WHEN c.activo = 1 THEN '🔴 OCUPADO' ELSE '🟢 LIBRE' END as Estado,
            CASE 
                WHEN c.activo = 1 THEN c.fecha_fin 
                ELSE 'DISPONIBLE HOY' 
            END as [Disponible Desde]
        FROM inmuebles i 
        JOIN bloques b ON i.id_bloque = b.id
        LEFT JOIN contratos c ON i.id = c.id_inmueble AND c.activo = 1
    """
    df = db_query(query_inv)

    if df is not None and not df.empty:
        c1, c2 = st.columns(2)
        total_u = len(df)
        libres_count = len(df[df['Estado'].str.contains('LIBRE', na=False)])
        
        c1.metric("Unidades Libres", libres_count)
        c2.metric("Total Unidades", total_u)
        
        # Formateo de moneda
        cols_money = ['Alquiler', 'Contrato', 'Deposito']
        for col in cols_money:
            if col in df.columns:
                df[col] = df[col].apply(f_m)
        
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No hay unidades cargadas en el sistema.")
