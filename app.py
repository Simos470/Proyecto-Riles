import streamlit as st
import pandas as pd
import json

# 1. CONFIGURACIÓN E IDENTIDAD
st.set_page_config(page_title="Validador RILES", page_icon="⚖️", layout="wide")

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

@st.cache_data
def cargar_normativa():
    try:
        with open('normativa.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error("🚨 Archivo 'normativa.json' no encontrado.")
        return {}

matriz_normativa = cargar_normativa()

if matriz_normativa:
    st.subheader("📍 1. Destino de la Descarga")

    destino_macro = st.radio(
        "¿Hacia dónde se dispondrán los riles?",
        ["Red de Alcantarillado (Sanitaria)", "Cuerpo de Agua Superficial / Mar"],
        horizontal=True
    )

    st.markdown("---")
    st.subheader("⚙️ 2. Parámetros del Receptor y Caudal")
    
    clave_seleccionada = None 
    clave_emisor = None # Nueva variable para el check de Emisor
    caudal_industrial = 0.0 # Variable global para cálculo de masa

    if destino_macro == "Red de Alcantarillado (Sanitaria)":
        st.caption("Evaluación de límites de descarga bajo D.S. 609")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            poblacion = st.selectbox(
                "Población del servicio sanitario:",
                ["Menor o igual a 100.000 habitantes", "Mayor a 100.000 habitantes"]
            )
        with col2:
            ptas = st.radio(
                "¿La red cuenta con Planta de Tratamiento (PTAS)?",
                ["Sí (Tabla 4)", "No (Tabla 3)"]
            )
        with col3:
            # INPUT CRÍTICO: Necesario para calcular g/día
            caudal_industrial = st.number_input(
                "Caudal medio de descarga (m³/día):", 
                min_value=0.0, value=10.0, step=1.0,
                help="Requerido para determinar si la carga supera el equivalente a 100 habitantes."
            )
            
        # LÓGICA DE MAPEO ALGORÍTMICO DS 609
        # 1. Tabla para evaluar si cumple descarga (Concentraciones)
        if ptas == "Sí (Tabla 4)":
            clave_seleccionada = "ds609_t4"
        else:
            clave_seleccionada = "ds609_t3"
            
        # 2. Tabla para evaluar si es emisor (Cargas)
        if poblacion == "Menor o igual a 100.000 habitantes":
            clave_emisor = "ds609_emisor_t1"
        else:
            clave_emisor = "ds609_emisor_t2"

    elif destino_macro == "Cuerpo de Agua Superficial / Mar":
        st.caption("Evaluación bajo criterios del D.S. 90")
        
        tipo_cuerpo = st.selectbox(
            "Tipo de cuerpo receptor:",
            ["Río", "Lago", "Mar (Zona Litoral)", "Mar (Fuera de Zona Litoral)"]
        )
        
        if tipo_cuerpo == "Lago": clave_seleccionada = "ds90_t3"
        elif tipo_cuerpo == "Mar (Zona Litoral)": clave_seleccionada = "ds90_t4"
        elif tipo_cuerpo == "Mar (Fuera de Zona Litoral)": clave_seleccionada = "ds90_t5"
        elif tipo_cuerpo == "Río":
            dilucion = st.checkbox("¿El río cuenta con capacidad de dilución probada?")
            if dilucion:
                caudal_rio = st.number_input("Caudal del río (m³/día):", min_value=0.0)
                clave_seleccionada = "ds90_t2"
            else:
                clave_seleccionada = "ds90_t1"

    st.markdown("---")
    
    if clave_seleccionada and clave_seleccionada in matriz_normativa:
        datos_norma = matriz_normativa[clave_seleccionada]
        parametros_norma = datos_norma["parametros"]

        st.subheader("🧪 3. Ingreso de Datos de Laboratorio (Efluente)")
        st.caption("Ingrese las concentraciones medidas. Los cálculos de carga (g/día) se harán automáticamente en segundo plano.")
        
        entradas_usuario = {}
        columnas_input = st.columns(4)
        
        for i, (param, specs) in enumerate(parametros_norma.items()):
            col = columnas_input[i % 4]
            with col:
                ayuda = specs.get("nota", "")
                entradas_usuario[param] = st.number_input(
                    f"{param} ({specs.get('unidad', '')})", 
                    value=0.0, step=0.1, help=ayuda, key=f"input_{param}"
                )

        st.markdown("---")
        st.subheader("📊 4. Informe de Validación Normativa")

        # ==========================================
        # MOTOR FASE 1: CHECK DE ESTABLECIMIENTO EMISOR (Solo DS 609)
        # ==========================================
        es_emisor = True # Por defecto True para DS 90
        causas_emisor = []
        
        if destino_macro == "Red de Alcantarillado (Sanitaria)" and clave_emisor in matriz_normativa:
            es_emisor = False # Asumimos inocencia hasta probar culpa
            datos_emisor = matriz_normativa[clave_emisor]["parametros"]
            
            for param, valor in entradas_usuario.items():
                if param in datos_emisor:
                    specs_emisor = datos_emisor[param]
                    
                    # Si la norma de emisor está en g/día, calculamos masa (Q x C)
                    if specs_emisor.get("unidad") == "g/dia":
                        carga_g_dia = valor * caudal_industrial
                        if "max" in specs_emisor and carga_g_dia > specs_emisor["max"]:
                            es_emisor = True
                            causas_emisor.append(f"{param} ({carga_g_dia:.1f} g/día)")
                            
                    # Si la norma es un absoluto (pH, Temp), evaluamos directo
                    elif "max" in specs_emisor and valor > specs_emisor["max"]:
                        es_emisor = True
                        causas_emisor.append(f"{param} (Medida absoluta)")

        # ==========================================
        # MOTOR FASE 2: CHECK DE CUMPLIMIENTO (Para todos)
        # ==========================================
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

        # ==========================================
        # DICTAMEN FINAL INTELIGENTE
        # ==========================================
        st.markdown("### 📝 Dictamen de Cumplimiento")
        
        if destino_macro == "Red de Alcantarillado (Sanitaria)":
            if not es_emisor:
                st.success("✅ **NO CALIFICA COMO ESTABLECIMIENTO EMISOR:** La carga contaminante calculada es inferior al equivalente de 100 hab/día. Legalmente, NO está obligado a cumplir los límites máximos de descarga del D.S. 609.")
            else:
                st.warning(f"⚠️ **SÍ ES ESTABLECIMIENTO EMISOR:** La industria supera la carga equivalente a 100 hab/día en los siguientes parámetros: **{', '.join(causas_emisor)}**. \n\nPor tanto, está obligada a cumplir la tabla de descargas correspondiente.")
                
                # Sub-dictamen de cumplimiento
                if estado_general == "NO CUMPLE":
                    st.error("🚨 **ALERTA CRÍTICA:** Como emisor, su efluente **EXCEDE** los límites permitidos para descargar en el alcantarillado. Se requiere retención o tratamiento inmediato.")
                else:
                    st.success("✅ **CUMPLE LA NORMATIVA:** Su industria es emisora, pero el efluente actual **CUMPLE** con las concentraciones máximas para descarga segura en alcantarillado.")
        else:
            # Dictamen simplificado para DS 90
            if estado_general == "NO CUMPLE":
                st.error("🚨 **ALERTA CRÍTICA:** Los valores ingresados exceden los límites máximos permitidos por el D.S. 90.")
            else:
                st.success("✅ **CUMPLE LA NORMATIVA:** Todos los parámetros se encuentran en rangos seguros según el D.S. 90.")