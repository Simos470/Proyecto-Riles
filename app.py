import streamlit as st
import pandas as pd
import json

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="Validador RILES", page_icon="⚖️", layout="wide")

# --- LIMPIEZA QUIRÚRGICA ---
hide_st_style = """
            <style>
            [data-testid="stDeployButton"] {display: none !important;}
            [data-testid="stStatusWidget"] {display: none !important;}
            footer {display: none !important;}
            [data-testid="stHeader"] {background-color: rgba(0,0,0,0) !important;}
            .block-container {padding-top: 2rem !important;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

st.title("⚖️ Motor de Validación Normativa RILES")
st.markdown("---")

# 2. CARGA DINÁMICA DE LA BASE DE DATOS
@st.cache_data
def cargar_normativa():
    # Asume que el archivo normativa.json está en el mismo directorio
    try:
        with open('normativa.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("🚨 Archivo 'normativa.json' no encontrado. Asegúrate de cargarlo en el directorio.")
        return {}

matriz_normativa = cargar_normativa()

if matriz_normativa:
    # 3. PASO 1: SELECCIÓN DEL MARCO REGULATORIO
    st.subheader("📍 1. Selección de Normativa y Escenario")
    
    # Crear un diccionario para mapear el "nombre" visible con la "clave" del JSON
    opciones_nombres = {datos["nombre"]: clave for clave, datos in matriz_normativa.items()}
    
    nombre_seleccionado = st.selectbox(
        "Seleccione el escenario normativo a evaluar:",
        list(opciones_nombres.keys()),
        help="Define la tabla de límites máximos que se aplicará al efluente o cálculo de carga."
    )
    
    # Extraer los datos específicos de la selección
    clave_seleccionada = opciones_nombres[nombre_seleccionado]
    datos_norma = matriz_normativa[clave_seleccionada]
    parametros_norma = datos_norma["parametros"]

    with st.expander("Ver detalle del marco regulatorio seleccionado", expanded=True):
        st.info(f"**Descripción:** {datos_norma['descripcion']}")

    st.markdown("---")

    # 4. PASO 2: CARACTERIZACIÓN DINÁMICA (Generación automática de inputs)
    st.subheader("🧪 2. Ingreso de Datos de Laboratorio / Terreno")
    st.caption("Ingrese los valores medidos. La unidad requerida se indica en cada parámetro.")
    
    entradas_usuario = {}
    
    # Agrupar inputs en 3 o 4 columnas para optimizar el espacio en pantalla
    columnas_input = st.columns(4)
    
    for i, (param, specs) in enumerate(parametros_norma.items()):
        col = columnas_input[i % 4]
        with col:
            # Si el parámetro tiene una nota (ej. Aluminio o Boro), la mostramos en el 'help'
            ayuda = specs.get("nota", "")
            
            # El input numérico: la etiqueta incluye la unidad automáticamente
            entradas_usuario[param] = st.number_input(
                f"{param} ({specs['unidad']})", 
                value=0.0, 
                step=0.1,
                help=ayuda
            )

    # 5. PASO 3: MOTOR DE EVALUACIÓN Y RESULTADOS
    st.markdown("---")
    st.subheader("📊 3. Informe de Validación y Análisis de Sensibilidad")

    filas_resultados = []
    estado_general = "CUMPLE"

    for param, valor in entradas_usuario.items():
        specs = parametros_norma[param]
        estado = "✔️ OK"
        limite_str = ""
        
        # Caso especial: pH u otros con rangos (min y max)
        if "min" in specs and "max" in specs:
            limite_str = f"[{specs['min']} - {specs['max']}]"
            if valor < specs["min"] or valor > specs["max"]:
                estado = "❌ EXCESO"
                estado_general = "NO CUMPLE"
            # Alerta de sensibilidad para pH (cerca de los bordes)
            elif (valor - specs["min"] <= 0.5) or (specs["max"] - valor <= 0.5):
                if valor != 0.0: # Evitar alerta falsa si está en 0 por defecto
                    estado = "⚠️ RIESGO MARGEN"
        
        # Caso estándar: Solo límite máximo
        elif "max" in specs:
            limite_str = str(specs["max"])
            if valor > specs["max"]:
                estado = "❌ EXCESO"
                estado_general = "NO CUMPLE"
            # Lógica de Semáforo: Alerta si supera el 90% del límite permitido
            elif valor >= specs["max"] * 0.9 and valor != 0.0:
                estado = "⚠️ ALERTA (>90%)"
        
        filas_resultados.append({
            "Parámetro": param,
            "Valor Medido": valor,
            "Unidad": specs["unidad"],
            "Límite Normativo": limite_str,
            "Diagnóstico": estado
        })

    # Mostrar tabla usando pandas
    df_resultados = pd.DataFrame(filas_resultados)
    
    # Aplicar color a la tabla (opcional, mejora la UX)
    def color_filas(val):
        if "❌" in str(val): return 'background-color: #ffcccc; color: black;'
        if "⚠️" in str(val): return 'background-color: #fff3cd; color: black;'
        return ''
    
    st.dataframe(df_resultados.style.map(color_filas), use_container_width=True)

    # 6. DICTAMEN FINAL JURÍDICO/TÉCNICO
    st.markdown("### 📝 Dictamen de Cumplimiento")
    if estado_general == "NO CUMPLE":
        st.error("🚨 **ALERTA CRÍTICA:** Los valores ingresados exceden los límites máximos permitidos por la normativa seleccionada. Se requiere ajuste de proceso o retención de efluente.")
    else:
        # Revisar si hay advertencias para no dar un simple "OK" si están al borde
        if any("⚠️" in r["Diagnóstico"] for r in filas_resultados):
            st.warning("✅ **CUMPLE CON OBSERVACIONES:** El vertido cumple la norma, pero algunos parámetros están en un umbral crítico (>90% del límite). Se recomienda análisis de sensibilidad.")
        else:
            st.success("✅ **CUMPLE LA NORMATIVA:** Todos los parámetros se encuentran en rangos de operación seguros según el marco regulatorio vigente.")