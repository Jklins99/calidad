import streamlit as st
from fpdf import FPDF
from PIL import Image
import sqlite3
import pandas as pd
import io
import os
import zipfile
from datetime import date, datetime

st.set_page_config(page_title="Control de Refuerzos - Clínica Aviva", layout="wide")

# ==========================================
# 1. CONFIGURACIÓN DE BASE DE DATOS Y CARPETAS
# ==========================================
DB_FILE = "bd_refuerzos_aviva.db"
IMG_DIR = "fotos_refuerzos"
os.makedirs(IMG_DIR, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS refuerzos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            nivel TEXT,
            sector TEXT,
            ambiente TEXT,
            eje_muro TEXT,
            tipo_refuerzo TEXT,
            especificacion TEXT,
            cota_altura TEXT,
            estado TEXT,
            observacion TEXT,
            foto_path TEXT,
            creado_en TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def guardar_imagen_disco(imagen_file, prefijo="ref"):
    if imagen_file is not None:
        img = Image.open(imagen_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((1200, 1200))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{prefijo}_{timestamp}.jpg"
        filepath = os.path.join(IMG_DIR, filename)
        img.save(filepath, format="JPEG", quality=80)
        return filepath
    return ""

def insertar_registro(datos):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO refuerzos (
            fecha, nivel, sector, ambiente, eje_muro, tipo_refuerzo,
            especificacion, cota_altura, estado, observacion, foto_path, creado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', datos)
    conn.commit()
    conn.close()

def leer_registros():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM refuerzos ORDER BY id DESC", conn)
    conn.close()
    return df

def eliminar_registro(id_reg):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT foto_path FROM refuerzos WHERE id = ?", (id_reg,))
    row = c.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        try:
            os.remove(row[0])
        except Exception:
            pass
    c.execute("DELETE FROM refuerzos WHERE id = ?", (id_reg,))
    conn.commit()
    conn.close()

# ==========================================
# 2. CLASE GENERADORA DE PDF (FPDF2)
# ==========================================
def limpiar_texto(texto):
    if texto is None:
        return ""
    reemplazos = {"–": "-", "—": "-", "“": '"', "”": '"', "‘": "'", "’": "'", "•": "-"}
    t = str(texto)
    for k, v in reemplazos.items():
        t = t.replace(k, v)
    return t.encode('latin-1', 'replace').decode('latin-1')

class ReportePDF(FPDF):
    def __init__(self, fecha_rep, responsable):
        super().__init__()
        self.fecha_rep = limpiar_texto(fecha_rep)
        self.responsable = limpiar_texto(responsable)

    def header(self):
        self.set_fill_color(20, 45, 76)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 8, limpiar_texto("  PROYECTO: CLÍNICA AVIVA - ESPECIALIDAD DRYWALL"), fill=True, new_x="LMARGIN", new_y="NEXT")
        self.set_font("Helvetica", "", 9)
        self.cell(0, 6, limpiar_texto(f"  INFORME DE CONTROL DE REFUERZOS Y PRE-CIERRE | Fecha: {self.fecha_rep} | Resp: {self.responsable}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, limpiar_texto(f"Control de Calidad y Producción Drywall - Clínica Aviva | Página {self.page_no()}/{{nb}}"), align="C")

def generar_pdf(df_filtrado, fecha_rep, responsable, nota_cierre, plano_file):
    pdf = ReportePDF(fecha_rep, responsable)
    pdf.alias_nb_pages()
    pdf.add_page()

    # 1. KPIs Resumen Ejecutivo
    total = len(df_filtrado)
    liberados = len(df_filtrado[df_filtrado["estado"].str.contains("Liberado", na=False)])
    observados = total - liberados
    ambientes_libres = df_filtrado[df_filtrado["estado"].str.contains("Liberado", na=False)]["ambiente"].nunique()

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 45, 76)
    pdf.cell(0, 6, limpiar_texto("1. RESUMEN EJECUTIVO DE AVANCE Y HABILITACIÓN DE FRENTES"), new_x="LMARGIN", new_y="NEXT")

    pdf.set_fill_color(240, 244, 248)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(47, 8, limpiar_texto(f"Total Puntos: {total}"), border=1, fill=True, align="C")
    pdf.set_text_color(0, 110, 50)
    pdf.cell(48, 8, limpiar_texto(f"Liberados: {liberados}"), border=1, fill=True, align="C")
    pdf.set_text_color(180, 40, 40)
    pdf.cell(48, 8, limpiar_texto(f"Bloqueados/Obs: {observados}"), border=1, fill=True, align="C")
    pdf.set_text_color(20, 45, 76)
    pdf.cell(47, 8, limpiar_texto(f"Ambientes Listos: {ambientes_libres}"), border=1, fill=True, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    if nota_cierre:
        pdf.set_fill_color(230, 247, 236)
        pdf.set_text_color(15, 85, 40)
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(0, 6, limpiar_texto(f"FRENTES HABILITADOS PARA CIERRE DE 2DA CARA (EMPLACADO): {nota_cierre}"), border=1, fill=True)
        pdf.ln(3)

    # 2. Plano en Planta (si se adjunta)
    if plano_file is not None:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(20, 45, 76)
        pdf.cell(0, 6, limpiar_texto("2. ESQUEMA / PLANO EN PLANTA INTERVENIDO"), new_x="LMARGIN", new_y="NEXT")
        img_p = Image.open(plano_file)
        if img_p.mode in ("RGBA", "P"):
            img_p = img_p.convert("RGB")
        img_p.thumbnail((1400, 900))
        b_plano = io.BytesIO()
        img_p.save(b_plano, format="JPEG", quality=85)
        b_plano.seek(0)
        pdf.image(b_plano, x=15, w=180)
        pdf.ln(4)

    # 3. Cuadro de trazabilidad
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(20, 45, 76)
    pdf.cell(0, 6, limpiar_texto("3. MATRIZ DE TRAZABILIDAD DE REFUERZOS EN TABIQUERÍA"), new_x="LMARGIN", new_y="NEXT")

    headers = [("Piso/Sec", 22), ("Ambiente", 35), ("Elemento / Tipo", 42), ("Madera/Espec.", 33), ("Cota/Alt.", 26), ("Estado", 32)]
    pdf.set_fill_color(20, 45, 76)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 8)
    for h, w in headers:
        pdf.cell(w, 7, limpiar_texto(h), border=1, fill=True, align="C")
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for _, row in df_filtrado.iterrows():
        pdf.set_text_color(0, 0, 0)
        piso_sec = f"{row['nivel']} / {row['sector']}"
        amb_eje = f"{row['ambiente']} ({row['eje_muro']})" if row['eje_muro'] else str(row['ambiente'])
        pdf.cell(22, 6, limpiar_texto(piso_sec)[:14], border=1)
        pdf.cell(35, 6, limpiar_texto(amb_eje)[:22], border=1)
        pdf.cell(42, 6, limpiar_texto(row['tipo_refuerzo'])[:26], border=1)
        pdf.cell(33, 6, limpiar_texto(row['especificacion'])[:20], border=1)
        pdf.cell(26, 6, limpiar_texto(row['cota_altura'])[:15], border=1, align="C")
        
        est = str(row['estado'])
        if "Liberado" in est:
            pdf.set_text_color(0, 110, 50)
        else:
            pdf.set_text_color(180, 40, 40)
        pdf.cell(32, 6, limpiar_texto(est)[:19], border=1, align="C", new_x="LMARGIN", new_y="NEXT")

    # 4. Panel Fotográfico de Respaldo (2 fotos por fila)
    df_fotos = df_filtrado[df_filtrado["foto_path"].notna() & (df_filtrado["foto_path"] != "")]
    df_fotos = df_fotos[df_fotos["foto_path"].apply(lambda p: os.path.exists(str(p)))]

    if not df_fotos.empty:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(20, 45, 76)
        pdf.cell(0, 7, limpiar_texto("4. PANEL FOTOGRÁFICO DE EVIDENCIA ANTES DE CIERRE (CON WINCHA)"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        fotos_list = df_fotos.to_dict("records")
        for i in range(0, len(fotos_list), 2):
            if pdf.get_y() > 210:
                pdf.add_page()
            y_top = pdf.get_y()
            
            for j in range(2):
                if i + j < len(fotos_list):
                    item = fotos_list[i + j]
                    x_pos = 12 if j == 0 else 108
                    try:
                        pdf.image(item["foto_path"], x=x_pos, y=y_top, w=88, h=58)
                    except Exception:
                        pass
                    pdf.set_xy(x_pos, y_top + 59)
                    pdf.set_font("Helvetica", "B", 8)
                    pdf.set_text_color(20, 45, 76)
                    titulo_f = f"{item['nivel']} - {item['ambiente']} ({item['tipo_refuerzo']})"
                    pdf.cell(88, 4, limpiar_texto(titulo_f)[:48], align="L", new_x="LMARGIN", new_y="NEXT")
                    
                    pdf.set_xy(x_pos, y_top + 63)
                    pdf.set_font("Helvetica", "", 7.5)
                    pdf.set_text_color(60, 60, 60)
                    detalle_f = f"Cota: {item['cota_altura']} | {item['especificacion']} | {item['observacion']}"
                    pdf.multi_cell(88, 3.5, limpiar_texto(detalle_f)[:110])

            pdf.set_y(y_top + 76)

    return bytes(pdf.output())

# ==========================================
# 3. INTERFAZ PRINCIPAL DE STREAMLIT
# ==========================================
st.title("🏗️ Control de Refuerzos de Madera y Pre-Cierre - Clínica Aviva")

tab1, tab2, tab3 = st.tabs([
    "📸 1. Captura en Campo (Cámara)", 
    "🗂️ 2. Historial Guardado y Filtros", 
    "📄 3. Generar Informe PDF"
])

# ------------------------------------------
# PESTAÑA 1: REGISTRO CON CÁMARA DIRECTA
# ------------------------------------------
with tab1:
    st.subheader("Registrar Punto de Refuerzo en Obra")
    
    # Selector de modo de captura fuera del form para que actualice en vivo
    modo_captura = st.radio(
        "Método de captura fotográfica:",
        ["📷 Abrir Cámara en Vivo", "🖼️ Subir foto / Cámara nativa HD del celular"],
        horizontal=True
    )

    if modo_captura == "📷 Abrir Cámara en Vivo":
        foto_capturada = st.camera_input("Toma la foto del refuerzo con la wincha visible")
    else:
        foto_capturada = st.file_uploader("En tu celular, pulsa aquí y elige 'Cámara' o 'Galería'", type=["jpg", "jpeg", "png"])

    with st.form("form_registro_campo", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            f_reg = st.date_input("Fecha", value=date.today())
            nivel = st.selectbox("Nivel / Piso", ["Sótano 1", "Sótano 2", "Piso 1", "Piso 2", "Piso 3", "Piso 4", "Piso 5", "Piso 6", "Azotea"])
            sector = st.selectbox("Sector", ["Sector A", "Sector B", "Sector C", "General"])
        with c2:
            ambiente = st.text_input("Ambiente (ej. Consultorio 304, SH Discap., Sala Rayos X)")
            eje_muro = st.text_input("Eje / Código de Muro en Plano (ej. Eje 4-B / Muro T-02)")
            tipo_ref = st.selectbox("Elemento a Soportar (Según Plano)", [
                "Lavatorio / Ovalín",
                "Barras de Apoyo SH Discapacitados",
                "Soporte de TV / Monitor Médico",
                "Mueble Alto / Repisa / Gabinete",
                "Camilla / Equipo Médico de Pared",
                "Dispensador / Papelero / Accesorios",
                "Marco de Puerta / Contramarco",
                "Otro Refuerzo Especial"
            ])
        with c3:
            especificacion = st.selectbox("Especificación de Madera / Plancha", [
                'Madera Tornillo 2" x 4" tratada',
                'Madera Tornillo 2" x 6" tratada',
                'Madera Tornillo 2" x 8" tratada',
                'Doble listón 2" x 4" + Plancha Metálica',
                'Fenólico / Triplay 18mm + Parantes'
            ])
            cota = st.text_input("Cota verificada con wincha (ej. H=0.85m al eje)")
            estado = st.selectbox("Estado para Cierre de 2da Cara", [
                "✅ Liberado para Emplacar",
                "⚠️ Bloqueado por MEP (Falta pase eléctrico/sanitario)",
                "❌ Observado (Falta fijación o fuera de cota)"
            ])

        observacion = st.text_input("Observación rápida (ej. Fijado con ángulos a parante cada 0.40m, listo para tapar)")
        
        btn_guardar = st.form_submit_button("💾 Guardar Punto en Base de Datos", use_container_width=True)

        if btn_guardar:
            if not ambiente.strip():
                st.warning("Por favor ingresa el nombre o número del Ambiente.")
            else:
                ruta_img = guardar_imagen_disco(foto_capturada)
                ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                datos_fila = (
                    f_reg.strftime("%Y-%m-%d"), nivel, sector, ambiente.strip(),
                    eje_muro.strip(), tipo_ref, especificacion, cota.strip(),
                    estado, observacion.strip(), ruta_img, ahora
                )
                insertar_registro(datos_fila)
                st.success(f"✅ ¡Guardado! {nivel} - {ambiente} ({tipo_ref}) se registró en la base de datos.")

# ------------------------------------------
# PESTAÑA 2: HISTORIAL GUARDADO Y BACKUP
# ------------------------------------------
with tab2:
    st.subheader("Base de Datos Acumulada de Refuerzos")
    df_todo = leer_registros()

    if df_todo.empty:
        st.info("Aún no hay registros guardados. Registra tu primer refuerzo en la Pestaña 1.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filtro_piso = st.multiselect("Filtrar por Piso", options=df_todo["nivel"].unique())
        with col_f2:
            filtro_estado = st.multiselect("Filtrar por Estado", options=df_todo["estado"].unique())
        with col_f3:
            filtro_fecha = st.multiselect("Filtrar por Fecha", options=df_todo["fecha"].unique())

        df_vista = df_todo.copy()
        if filtro_piso:
            df_vista = df_vista[df_vista["nivel"].isin(filtro_piso)]
        if filtro_estado:
            df_vista = df_vista[df_vista["estado"].isin(filtro_estado)]
        if filtro_fecha:
            df_vista = df_vista[df_vista["fecha"].isin(filtro_fecha)]

        st.dataframe(df_vista.drop(columns=["foto_path"]), use_container_width=True)

        # Descargar en CSV (Excel)
        csv_bytes = df_vista.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar Tabla en Excel (CSV)", data=csv_bytes, file_name="historial_refuerzos_aviva.csv", mime="text/csv")

        st.markdown("---")
        with st.expander("🗑️ Eliminar un registro equivocado"):
            id_borrar = st.number_input("Ingresa el ID del registro a borrar", min_value=1, step=1)
            if st.button("Eliminar ID seleccionado"):
                eliminar_registro(id_borrar)
                st.success(f"Registro ID {id_borrar} eliminado. Recarga o cambia de filtro para ver la tabla actualizada.")
                st.rerun()

    st.markdown("---")
    st.markdown("#### 🛡️ Copia de Seguridad (Backup de Base de Datos + Fotos)")
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if os.path.exists(DB_FILE):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(DB_FILE)
                for root, _, files in os.walk(IMG_DIR):
                    for f in files:
                        zf.write(os.path.join(root, f))
            zip_buffer.seek(0)
            st.download_button(
                "📦 Descargar Backup Completo (.zip)",
                data=zip_buffer.getvalue(),
                file_name=f"backup_refuerzos_aviva_{date.today()}.zip",
                mime="application/zip"
            )
    with col_b2:
        zip_subido = st.file_uploader("Restaurar Backup (.zip) previo", type=["zip"])
        if zip_subido is not None:
            if st.button("🔄 Restaurar Datos y Fotos"):
                with zipfile.ZipFile(zip_subido, "r") as zf:
                    zf.extractall(".")
                st.success("¡Base de datos y fotos restauradas con éxito!")
                st.rerun()

# ------------------------------------------
# PESTAÑA 3: GENERAR INFORME PDF DEL DÍA
# ------------------------------------------
with tab3:
    st.subheader("Generar Reporte Ejecutivo en PDF para Jefatura / Producción")
    df_rep = leer_registros()

    if df_rep.empty:
        st.warning("Primero guarda al menos un registro en la Pestaña 1 para generar el PDF.")
    else:
        c_p1, c_p2 = st.columns(2)
        with c_p1:
            fechas_disp = df_rep["fecha"].unique().tolist()
            fechas_sel = st.multiselect("Selecciona Fecha(s) a incluir en el PDF:", options=fechas_disp, default=[fechas_disp[0]])
            pisos_disp = df_rep["nivel"].unique().tolist()
            pisos_sel = st.multiselect("Selecciona Nivel(es) a incluir:", options=pisos_disp, default=pisos_disp)
        with c_p2:
            responsable_rep = st.text_input("Responsable del Reporte", value="Ing. Jefferson Klinsman Lapa Espino")
            nota_habilitados = st.text_area(
                "Resumen de Ambientes Listos para Cerrar 2da Cara mañana:",
                value="Se encuentran habilitados al 100% de refuerzos los ambientes listados como 'Liberado para Emplacar'. Listos para ingreso de cuadrilla de forro."
            )

        plano_img = st.file_uploader("🗺️ Opcional: Subir recorte o foto del Plano en Planta intervenido hoy", type=["jpg", "jpeg", "png"])

        df_final_pdf = df_rep[df_rep["fecha"].isin(fechas_sel) & df_rep["nivel"].isin(pisos_sel)]
        st.info(f"Se incluirán **{len(df_final_pdf)} puntos de refuerzo** en el informe PDF.")

        if st.button("🚀 Generar y Preparar Informe PDF", use_container_width=True):
            if df_final_pdf.empty:
                st.error("No hay registros con esos filtros.")
            else:
                fecha_str = ", ".join(fechas_sel)
                pdf_bytes = generar_pdf(df_final_pdf, fecha_str, responsable_rep, nota_habilitados, plano_img)
                st.success("✅ ¡PDF Generado correctamente!")
                st.download_button(
                    label="📥 Descargar Informe Diario en PDF",
                    data=pdf_bytes,
                    file_name=f"Informe_Refuerzos_Aviva_{date.today()}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )