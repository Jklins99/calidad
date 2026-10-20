import streamlit as st
import pandas as pd
from fpdf import FPDF
from PIL import Image
import io
from datetime import date

st.set_page_config(page_title="Control de Refuerzos y Pre-Cierre - Clínica Aviva", layout="wide")

st.title("🏗️ Generador de Informe Diario en PDF: Refuerzos y Pre-Cierre")
st.caption("Proyecto: Clínica Aviva | Especialidad: Tabiquería Drywall | Ing. Jefferson Lapa Espino")

# Inicializar tabla dinámica en sesión
if "df_refuerzos" not in st.session_state:
    st.session_state.df_refuerzos = pd.DataFrame([
        {"Cod": "REF-01", "Ambiente": "Consultorio 301", "Ejes": "A-B / 1-2", "Equipo / Uso": "Lavatorio Clínico", "Madera / Sección": 'Tornillo 2"x6"', "Cota H (m)": "0.85 m", "Estado": "HABILITADO CIERRE"},
        {"Cod": "REF-02", "Ambiente": "Consultorio 301", "Ejes": "B / 1-2", "Equipo / Uso": 'Soporte TV / Monitor 55"', "Madera / Sección": 'Tornillo 2"x8"', "Cota H (m)": "1.65 m", "Estado": "HABILITADO CIERRE"},
        {"Cod": "REF-03", "Ambiente": "SH Discap. 302", "Ejes": "B-C / 2", "Equipo / Uso": "Barras de Apoyo INDECOPI", "Madera / Sección": 'Tornillo 2"x8"', "Cota H (m)": "0.75 m", "Estado": "HABILITADO CIERRE"},
        {"Cod": "REF-04", "Ambiente": "Tópico 303", "Ejes": "C-D / 1", "Equipo / Uso": "Consola Gases Medicinales", "Madera / Sección": 'Doble 2"x6"', "Cota H (m)": "1.45 m", "Estado": "PENDIENTE MEP"},
    ])

# --- 1. DATOS GENERALES DEL REPORTE ---
with st.expander("📌 1. Datos de Cabecera y KPIs de Producción", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    correlativo = c1.text_input("N° de Reporte", "INF-REF-001")
    fecha_rep = c2.date_input("Fecha", date.today())
    nivel_sector = c3.text_input("Nivel y Sector", "Piso 3 - Sector A")
    plano_ref = c4.text_input("Plano en Planta Ref.", "Lámina A-301 (Planta de Refuerzos)")

    k1, k2, k3, k4 = st.columns(4)
    kpi_und = k1.text_input("Refuerzos Instalados Hoy", "18 und.")
    kpi_amb = k2.text_input("Ambientes Listos p/ 2da Cara", "5 Ambientes")
    kpi_m2 = k3.text_input("Metrado Habilitado Emplacado", "42.50 m²")
    kpi_obs = k4.text_input("Ambientes con Restricción MEP", "2 Ambientes")

# --- 2. TABLA EDITABLE DE REFUERZOS SEGÚN PLANO ---
st.subheader("📋 2. Registro de Refuerzos Verificados según Plano en Planta")
st.info("Puedes agregar, editar o borrar filas directamente en la tabla (como en Excel).")
df_editado = st.data_editor(
    st.session_state.df_refuerzos,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Estado": st.column_config.SelectboxColumn(
            "Estado Cierre",
            options=["HABILITADO CIERRE", "PENDIENTE MEP", "OBSERVADO"],
            required=True
        )
    }
)

# --- 3. NOTAS DE PRODUCCIÓN Y RESTRICCIONES ---
col_a, col_b = st.columns(2)
with col_a:
    frentes_libres = st.text_area(
        "✔ Ambientes 100% liberados para cerrar 2da cara mañana:",
        "Consultorio 301, SH Discapacitados 302 y Pasadizo Eje A-C. Todos los refuerzos según plano en planta están instalados y acotados."
    )
with col_b:
    restricciones = st.text_area(
        "⚠ Restricciones / Bloqueos por otras especialidades (MEP):",
        "En Tópico 303 (Eje C-D) falta liberación de tubería de cobre (Gases Medicinales) para colocar refuerzo de consola."
    )

# --- 4. CARGA DEL PLANO EN PLANTA Y FOTOS CON WINCHA ---
st.subheader("🗺️ 3. Captura del Plano en Planta y Evidencia Fotográfica")
img_plano = st.file_uploader("Subir recorte/captura del Plano en Planta (JPG/PNG)", type=["jpg", "jpeg", "png"])

st.markdown("##### 📸 Fotos de Campo (con wincha antes de emplacar 2da cara)")
fc1, fc2 = st.columns(2)
with fc1:
    f1 = st.file_uploader("Foto 1", type=["jpg", "jpeg", "png"], key="f1")
    d1 = st.text_input("Leyenda Foto 1", "Consultorio 301: Refuerzo 2x6 lavatorio H=0.85m")
    f3 = st.file_uploader("Foto 3", type=["jpg", "jpeg", "png"], key="f3")
    d3 = st.text_input("Leyenda Foto 3", "SH Discap. 302: Refuerzo 2x8 barras de apoyo H=0.75m")
with fc2:
    f2 = st.file_uploader("Foto 2", type=["jpg", "jpeg", "png"], key="f2")
    d2 = st.text_input("Leyenda Foto 2", "Consultorio 301: Doble refuerzo 2x8 TV H=1.65m")
    f4 = st.file_uploader("Foto 4", type=["jpg", "jpeg", "png"], key="f4")
    d4 = st.text_input("Leyenda Foto 4", "Tópico 303: Pendiente pase gases medicinales")


# --- FUNCIÓN PARA COMPRIMIR IMÁGENES EN MEMORIA ---
def optimizar_imagen(uploaded_file, max_size=(1200, 900)):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(max_size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    buf.seek(0)
    return buf


# --- CLASE GENERADORA DEL PDF ---
class ReportePDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_fill_color(15, 23, 42)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, "  PROYECTO CLÍNICA AVIVA - INFORME DIARIO DE REFUERZOS Y PRE-CIERRE DRYWALL", border=0, ln=1, fill=True)
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, f"Elaborado por: Ing. Jefferson Klinsman Lapa Espino | Página {self.page_no()}", align="C")


def construir_pdf():
    pdf = ReportePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # Datos de cabecera
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(48, 6, f"Reporte N°: {correlativo}", border=1)
    pdf.cell(45, 6, f"Fecha: {fecha_rep.strftime('%d/%m/%Y')}", border=1)
    pdf.cell(47, 6, f"Nivel: {nivel_sector}", border=1)
    pdf.cell(50, 6, f"Plano: {plano_ref[:22]}", border=1, ln=1)
    pdf.ln(3)

    # KPIs
    pdf.set_fill_color(241, 245, 249)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.cell(47.5, 7, f"Instalados Hoy: {kpi_und}", border=1, fill=True)
    pdf.cell(47.5, 7, f"Liberados 2da Cara: {kpi_amb}", border=1, fill=True)
    pdf.cell(47.5, 7, f"Metrado Listo: {kpi_m2}", border=1, fill=True)
    pdf.cell(47.5, 7, f"Restricción MEP: {kpi_obs}", border=1, ln=1, fill=True)
    pdf.ln(4)

    # Sección 1: Plano en Planta (si se subió)
    if img_plano is not None:
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, " 1. UBICACIÓN EN PLANO EN PLANTA (ZONAS INTERVENIDAS)", ln=1, fill=True)
        pdf.ln(2)
        buf_plano = optimizar_imagen(img_plano, max_size=(1600, 900))
        pdf.image(buf_plano, x=15, w=180, h=62)
        pdf.ln(3)

    # Sección 2: Tabla de Refuerzos
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 6, " 2. CUADRO DE TRAZABILIDAD DE REFUERZOS DE MADERA SEGÚN PLANO", ln=1, fill=True)
    
    # Cabecera Tabla
    pdf.set_fill_color(226, 232, 240)
    pdf.set_text_color(15, 23, 42)
    pdf.set_font("Helvetica", "B", 8)
    widths = [16, 36, 22, 46, 28, 18, 24]
    headers = ["Cód.", "Ambiente", "Ejes", "Equipo / Uso", "Sección", "Cota H", "Estado"]
    for w, h in zip(widths, headers):
        pdf.cell(w, 6, h, border=1, fill=True)
    pdf.ln()

    # Filas Tabla
    pdf.set_font("Helvetica", "", 8)
    for _, row in df_editado.iterrows():
        pdf.cell(widths[0], 5.5, str(row.get("Cod", ""))[:10], border=1)
        pdf.cell(widths[1], 5.5, str(row.get("Ambiente", ""))[:22], border=1)
        pdf.cell(widths[2], 5.5, str(row.get("Ejes", ""))[:13], border=1)
        pdf.cell(widths[3], 5.5, str(row.get("Equipo / Uso", ""))[:28], border=1)
        pdf.cell(widths[4], 5.5, str(row.get("Madera / Sección", ""))[:16], border=1)
        pdf.cell(widths[5], 5.5, str(row.get("Cota H (m)", ""))[:10], border=1)
        pdf.cell(widths[6], 5.5, str(row.get("Estado", ""))[:15], border=1, ln=1)
    pdf.ln(4)

    # Resumen de Producción y Restricciones
    pdf.set_fill_color(220, 252, 231)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.multi_cell(0, 5, f"FRENTES HABILITADOS PARA CIERRE DE 2DA CARA: {frentes_libres}", border=1, fill=True)
    pdf.ln(2)
    pdf.set_fill_color(254, 243, 199)
    pdf.multi_cell(0, 5, f"RESTRICCIONES DETECTADAS EN CAMPO: {restricciones}", border=1, fill=True)

    # Página 2: Panel Fotográfico (si hay fotos)
    fotos = [(f1, d1), (f2, d2), (f3, d3), (f4, d4)]
    fotos_validas = [(f, d) for f, d in fotos if f is not None]
    if fotos_validas:
        pdf.add_page()
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(0, 6, " 3. PANEL FOTOGRÁFICO DE ELEMENTOS OCULTOS (VERIFICACIÓN CON WINCHA)", ln=1, fill=True)
        pdf.ln(4)

        pdf.set_text_color(15, 23, 42)
        pdf.set_font("Helvetica", "", 8.5)
        for idx, (archivo_foto, leyenda) in enumerate(fotos_validas):
            col = idx % 2
            row_idx = idx // 2
            x_pos = 12 if col == 0 else 108
            y_pos = 32 + (row_idx * 95)

            buf_img = optimizar_imagen(archivo_foto)
            pdf.image(buf_img, x=x_pos, y=y_pos, w=88, h=66)
            pdf.set_xy(x_pos, y_pos + 68)
            pdf.multi_cell(88, 4.5, f"Foto {idx+1}: {leyenda}", border=1)

    return bytes(pdf.output())


st.markdown("---")
if st.button("🚀 Generar Informe Diario en PDF", type="primary"):
    pdf_bytes = construir_pdf()
    nombre_pdf = f"{correlativo}_{nivel_sector}.pdf".replace(" ", "_")
    st.success("¡PDF generado correctamente! Listo para enviar por WhatsApp o Correo.")
    st.download_button(
        label="📥 Descargar PDF Ahora",
        data=pdf_bytes,
        file_name=nombre_pdf,
        mime="application/pdf"
    )