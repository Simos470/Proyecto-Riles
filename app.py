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
    try:
        with open('normativa.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("🚨 Archivo 'normativa.json' no encontrado. Asegúrate de cargarlo en el directorio.")
        return {}

matriz_normativa = cargar_normativa()

if matriz_normativa:
    # 3. PASO 1 Y 2: ÁRBOL DE DECISIÓN (UI)
    st.subheader("📍 1. Destino de la Descarga")

    destino_macro = st.radio(
        "¿Hacia dónde se dispondrán los riles?",
        ["Red de Alcantarillado (Sanitaria)", "Cuerpo de Agua Superficial / Mar"],
        horizontal=True
    )

    st.markdown("---")
    st.subheader("⚙️ 2. Parámetros del Receptor")
    
    # Variable crucial que conectará la UI con el JSON
    clave_seleccionada = None 

    if destino_macro == "Red de Alcantarillado (Sanitaria)":
        st.caption("Evaluación de límites de descarga bajo D.S. 609")
        
        col1, col2 = st.columns(2)
        with col1:
            poblacion = st.selectbox(
                "Población del servicio sanitario:",
                ["Menor o igual a 100.000 habitantes", "Mayor a 100.000 habitantes"]
            )
            # Nota: La población se usará más adelante para calcular si es "Establecimiento Emisor" (Cargas QxC).
            
        with col2:
            ptas = st.radio(
                "¿La red cuenta con Planta de Tratamiento (PTAS)?",
                ["Sí (Tabla 4)", "No (Tabla 3)"]
            )
            
        # Lógica de mapeo para DS 609
        if ptas == "Sí (Tabla 4)":
            clave_seleccionada = "ds609_t4"
        else:
            clave_seleccionada = "ds609_t3"

    elif destino_macro == "Cuerpo de Agua Superficial / Mar":
        st.caption("Evaluación bajo criterios del D.S. 90")
        
        tipo_cuerpo = st.selectbox(
            "Tipo de cuerpo receptor:",
            ["Río", "Lago", "Mar (Zona Litoral)", "Mar (Fuera de Zona Litoral)"]
        )
        
        # Lógica de mapeo para DS 90
        if tipo_cuerpo == "Lago":
            clave_seleccionada = "ds90_t3"
        elif tipo_cuerpo == "Mar (Zona Litoral)":
            clave_seleccionada = "ds90_t4" # Asegúrate de que esta clave exista en tu JSON
        elif tipo_cuerpo == "Mar (Fuera de Zona Litoral)":
            clave_seleccionada = "ds90_t5" # Asegúrate de que esta clave exista en tu JSON
        elif tipo_cuerpo == "Río":
            dilucion = st.checkbox("¿El río cuenta con capacidad de dilución probada?")
            
            if dilucion:
                caudal_rio = st.number_input("Ingrese el caudal del río (m³/día):", min_value=0.0)
                st.info("💡 El algoritmo usará este caudal para recalcular los límites permitidos (Próxima actualización).")
                clave_seleccionada = "ds90_t2" # Río con dilución
            else:
                st.warning("⚠️ Se aplicarán los límites estrictos de la Tabla 1 (Sin dilución).")
                clave_seleccionada = "ds90_t1" # Río sin dilución

    # 4. PASO 3: EXTRACCIÓN Y GENERACIÓN DINÁMICA
    st.markdown("---")
    
    # Validamos que la clave deducida realmente exista en el JSON cargado
    if clave_seleccionada and clave_seleccionada in matriz_normativa:
        datos_norma = matriz_normativa[clave_seleccionada]
        parametros_norma = datos_norma["parametros"]

        with st.expander(f"Ver detalle: {datos_norma['nombre']}", expanded=False):
            st.info(f"**Descripción:** {datos_norma['descripcion']}")

        st.subheader("🧪 3. Ingreso de Datos de Laboratorio / Terreno")
        st.caption("Ingrese los valores medidos en el efluente.")
        
        entradas_usuario = {}
        columnas_input = st.columns(4)
        
        for i, (param, specs) in enumerate(parametros_norma.items()):
            col = columnas_input[i % 4]
            with col:
                ayuda = specs.get("nota", "")
                entradas_usuario[param] = st.number_input(
                    f"{param} ({specs.get('unidad', '')})", 
                    value=0.0, 
                    step=0.1,
                    help=ayuda,
                    key=f"input_{param}" # Buena práctica en Streamlit para evitar conflictos de ID
                )

        # 5. PASO 4: MOTOR DE EVALUACIÓN
        st.markdown("---")
        st.subheader("📊 4. Informe de Validación y Análisis de Sensibilidad")

        filas_resultados = []
        estado_general = "CUMPLE"

        for param, valor in entradas_usuario.items():
            specs = parametros_norma[param]
            estado = "✔️ OK"
            limite_str = ""
            
            if "min" in specs and "max" in specs:
                limite_str = f"[{specs['min']} - {specs['max']}]"
                if valor < specs["min"] or valor > specs["max"]:
                    estado = "❌ EXCESO"
                    estado_general = "NO CUMPLE"
                elif (valor - specs["min"] <= 0.5) or (specs["max"] - valor <= 0.5):
                    if valor != 0.0:
                        estado = "⚠️ RIESGO MARGEN"
            
            elif "max" in specs:
                limite_str = str(specs["max"])
                if valor > specs["max"]:
                    estado = "❌ EXCESO"
                    estado_general = "NO CUMPLE"
                elif valor >= specs["max"] * 0.9 and valor != 0.0:
                    estado = "⚠️ ALERTA (>90%)"
            
            filas_resultados.append({
                "Parámetro": param,
                "Valor Medido": valor,
                "Unidad": specs.get("unidad", ""),
                "Límite Normativo": limite_str,
                "Diagnóstico": estado
            })

        df_resultados = pd.DataFrame(filas_resultados)
        
        def color_filas(val):
            if "❌" in str(val): return 'background-color: #ffcccc; color: black;'
            if "⚠️" in str(val): return 'background-color: #fff3cd; color: black;'
            return ''
        
        st.dataframe(df_resultados.style.map(color_filas), use_container_width=True)

        st.markdown("### 📝 Dictamen de Cumplimiento")
        if estado_general == "NO CUMPLE":
            st.error("🚨 **ALERTA CRÍTICA:** Los valores ingresados exceden los límites máximos permitidos.")
        else:
            if any("⚠️" in r["Diagnóstico"] for r in filas_resultados):
                st.warning("✅ **CUMPLE CON OBSERVACIONES:** El vertido cumple la norma, pero algunos parámetros están en un umbral crítico (>90%).")
            else:
                st.success("✅ **CUMPLE LA NORMATIVA:** Todos los parámetros se encuentran en rangos seguros.")
    else:
        # Mensaje de seguridad por si seleccionan algo que aún no has cargado en el JSON
        st.info("📌 Seleccione un escenario válido o verifique que la tabla correspondiente esté cargada en la base de datos (JSON).")