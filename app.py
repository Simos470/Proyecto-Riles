import streamlit as st
import pandas as pd

# Configuración con identidad institucional
st.set_page_config(page_title="Sistema de Validación RILES", page_icon="⚖️", layout="wide")

st.title("⚖️ Sistema de Validación de Cumplimiento: Normas de Emisión")
st.markdown("""
    *Herramienta técnica para la verificación de parámetros físico-químicos según la normativa ambiental vigente de la República de Chile.*
""")
st.markdown("---")

# 1. MATRIZ DE CUERPOS RECEPTORES (Lenguaje basado en DS 90, DS 609 y DS 46)
# Definimos la relación técnica entre la naturaleza del vertido y su marco legal
MATRIZ_NORMATIVA = {
    "Sistemas de Alcantarillado (DS 609/98)": {
        "decreto": "D.S. N° 609/98",
        "descripcion": "Norma de emisión de contaminantes asociados a descargas de residuos líquidos a sistemas de alcantarillado.",
        "tabla": "Tabla N° 1 (Descargas con tratamiento de aguas servidas)",
        "limites": {
            "pH": [5.5, 9.0],
            "Temperatura": 35.0,
            "DBO5": 300.0,
            "DQO": 600.0,
            "Aceites y Grasas": 150.0,
            "Sólidos Suspendidos Totales": 300.0
        }
    },
    "Cuerpos de Agua Continentales Superficiales (DS 90/00)": {
        "decreto": "D.S. N° 90/00",
        "descripcion": "Norma de emisión para la regulación de contaminantes asociados a las descargas de residuos líquidos a aguas marinas y continentales superficiales.",
        "tabla": "Tabla N° 1 (Dentro de la zona de protección litoral)",
        "limites": {
            "pH": [6.0, 8.5],
            "Temperatura": 30.0,
            "DBO5": 35.0,
            "DQO": 120.0,
            "Aceites y Grasas": 20.0,
            "Sólidos Suspendidos Totales": 80.0
        }
    },
    "Cuerpos de Agua Marinos (DS 90/00)": {
        "decreto": "D.S. N° 90/00",
        "descripcion": "Norma de emisión para descargas de residuos líquidos a aguas marinas.",
        "tabla": "Tabla N° 3 (Descargas fuera de la zona de protección litoral)",
        "limites": {
            "pH": [6.0, 9.0],
            "Temperatura": 35.0,
            "DBO5": 100.0,
            "DQO": 250.0,
            "Aceites y Grasas": 50.0,
            "Sólidos Suspendidos Totales": 100.0
        }
    }
}

# 2. PANEL DE CONFIGURACIÓN DEL PUNTO DE VERTIDO
st.sidebar.header("📋 Identificación del Punto de Vertido")
cuerpo_receptor = st.sidebar.selectbox(
    "Naturaleza del Cuerpo Receptor:",
    list(MATRIZ_NORMATIVA.keys())
)

datos_norma = MATRIZ_NORMATIVA[cuerpo_receptor]

# Display de referencia normativa para generar confianza
with st.expander("ℹ️ Referencia del Marco Regulatorio Aplicable", expanded=False):
    st.write(f"**Norma de Emisión:** {datos_norma['decreto']}")
    st.write(f"**Descripción:** {datos_norma['descripcion']}")
    st.write(f"**Referencia:** {datos_norma['tabla']}")

# 3. CARACTERIZACIÓN DEL EFLUENTE (Ingreso de Datos de Laboratorio)
st.subheader("🧪 Caracterización Físico-Química del Efluente")
st.info("Ingrese los valores obtenidos en el reporte de monitoreo para su validación.")

col1, col2, col3 = st.columns(3)

with col1:
    in_ph = st.number_input("Potencial de Hidrógeno (pH)", value=7.0, step=0.1, help="Medido en unidades de pH")
    in_temp = st.number_input("Temperatura (°C)", value=20.0, step=1.0)

with col2:
    in_dbo5 = st.number_input("Demanda Bioquímica de Oxígeno (DBO5)", value=0.0, help="Medido en mg/L O2")
    in_dqo = st.number_input("Demanda Química de Oxígeno (DQO)", value=0.0, help="Medido en mg/L O2")

with col3:
    in_ayg = st.number_input("Aceites y Grasas (AyG)", value=0.0, help="Medido en mg/L")
    in_ss = st.number_input("Sólidos Suspendidos Totales (SST)", value=0.0, help="Medido en mg/L")

# 4. ANÁLISIS TÉCNICO DE CUMPLIMIENTO
st.markdown("---")
st.subheader("📊 Informe de Validación Normativa")

entradas = {
    "pH": in_ph,
    "Temperatura": in_temp,
    "DBO5": in_dbo5,
    "DQO": in_dqo,
    "Aceites y Grasas": in_ayg,
    "Sólidos Suspendidos Totales": in_ss
}

limites = datos_norma["limites"]
filas_informe = []

for param, valor in entradas.items():
    limite = limites[param]
    cumple = True
    observacion = "Cumple"
    
    if param == "pH":
        if valor < limite[0] or valor > limite[1]:
            cumple = False
            observacion = f"Desviación de Rango [{limite[0]} - {limite[1]}]"
    else:
        if valor > limite:
            cumple = False
            exceso = valor - limite
            porcentaje = (exceso / limite) * 100
            observacion = f"Exceso sobre LMP: {exceso:.2f} mg/L (+{porcentaje:.1f}%)"

    filas_informe.append({
        "Parámetro de Control": param,
        "Valor Reportado": valor,
        "Límite Máximo Permitido (LMP)": str(limite),
        "Estado": "✔️ DENTRO DE NORMA" if cumple else "❌ FUERA DE NORMA",
        "Observaciones Técnicas": observacion
    })

# Visualización del informe técnico
df_informe = pd.DataFrame(filas_informe)
st.table(df_informe)

# 5. DICTAMEN FINAL
if any("❌" in r["Estado"] for r in filas_informe):
    st.error("🚨 DICTAMEN: El vertido NO CUMPLE con los parámetros de la norma de emisión seleccionada.")
else:
    st.success("✅ DICTAMEN: El vertido se encuentra DENTRO DE LOS LÍMITES de la norma de emisión seleccionada.")