import streamlit as st
import pandas as pd

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="Validador RILES", page_icon="⚖️", layout="centered")

# --- LIMPIEZA QUIRÚRGICA ---
hide_st_style = """
            <style>
            [data-testid="stDeployButton"] {display: none !important;}
            [data-testid="stStatusWidget"] {display: none !important;}
            footer {display: none !important;}
            [data-testid="stHeader"] {background-color: rgba(0,0,0,0) !important;}
            /* Ajuste para que en móvil no se vea apretado */
            .block-container {padding-top: 2rem !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("⚖️ Validación de Cumplimiento RILES")
st.markdown("---")

# 2. DEFINICIÓN DE MATRIZ (Mantenemos tu lógica potente)
MATRIZ_NORMATIVA = {
    "Sistemas de Alcantarillado (DS 609/98)": {
        "decreto": "D.S. N° 609/98",
        "tabla": "Tabla N° 1",
        "limites": {"pH": [5.5, 9.0], "Temperatura": 35.0, "DBO5": 300.0, "DQO": 600.0, "AyG": 150.0, "SST": 300.0}
    },
    "Cuerpos de Agua Continentales (DS 90/00)": {
        "decreto": "D.S. N° 90/00",
        "tabla": "Tabla N° 1",
        "limites": {"pH": [6.0, 8.5], "Temperatura": 30.0, "DBO5": 35.0, "DQO": 120.0, "AyG": 20.0, "SST": 80.0}
    },
    "Aguas Marinas (DS 90/00)": {
        "decreto": "D.S. N° 90/00",
        "tabla": "Tabla N° 3",
        "limites": {"pH": [6.0, 9.0], "Temperatura": 35.0, "DBO5": 100.0, "DQO": 250.0, "AyG": 50.0, "SST": 100.0}
    }
}

# 3. PASO 1: SELECCIÓN DEL CUERPO RECEPTOR (Ahora en el centro)
st.subheader("📍 1. Destino del Vertido")
cuerpo_receptor = st.selectbox(
    "Seleccione la naturaleza del Cuerpo Receptor:",
    list(MATRIZ_NORMATIVA.keys()),
    help="Define el marco legal y los límites máximos permitidos."
)

datos_norma = MATRIZ_NORMATIVA[cuerpo_receptor]

# Breve info del decreto seleccionado
st.caption(f"Aplicando: **{datos_norma['decreto']}** ({datos_norma['tabla']})")

with st.expander("Ver detalle del marco regulatorio"):
    st.write(f"Esta sección valida los parámetros según los límites establecidos en el {datos_norma['decreto']} para {cuerpo_receptor.lower()}.")

st.markdown("---")

# 4. PASO 2: CARACTERIZACIÓN (Entrada de datos)
st.subheader("🧪 2. Caracterización del Efluente")
col1, col2 = st.columns(2)

with col1:
    in_ph = st.number_input("pH", value=7.0, step=0.1)
    in_temp = st.number_input("Temp. (°C)", value=20.0)
    in_dbo5 = st.number_input("DBO5 (mg/L)", value=0.0)

with col2:
    in_dqo = st.number_input("DQO (mg/L)", value=0.0)
    in_ayg = st.number_input("AyG (mg/L)", value=0.0)
    in_sst = st.number_input("SST (mg/L)", value=0.0)

# 5. PASO 3: RESULTADOS
st.markdown("---")
st.subheader("📊 3. Informe de Validación")

entradas = {
    "pH": in_ph, "Temperatura": in_temp, "DBO5": in_dbo5, 
    "DQO": in_dqo, "AyG": in_ayg, "SST": in_sst
}

limites = datos_norma["limites"]
filas = []

for param, valor in entradas.items():
    limite = limites[param]
    cumple = True
    if param == "pH":
        if valor < limite[0] or valor > limite[1]: cumple = False
    elif valor > limite: cumple = False
    
    filas.append({
        "Parámetro": param,
        "Valor": valor,
        "Límite": str(limite),
        "Estado": "✔️ OK" if cumple else "❌ EXCESO"
    })

st.table(pd.DataFrame(filas))

# Dictamen final
if any("❌" in r["Estado"] for r in filas):
    st.error("🚨 EL VERTIDO NO CUMPLE LA NORMA")
else:
    st.success("✅ EL VERTIDO CUMPLE LA NORMA")