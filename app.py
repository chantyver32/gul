import streamlit as st
import sqlite3
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA (Debe ir primero) ---
st.set_page_config(page_title="English Tutor Pro", page_icon="⚡", layout="wide")

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('english_practice.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS practice_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_text TEXT,
            correction TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def save_to_db(conn, user_text, correction):
    c = conn.cursor()
    c.execute("INSERT INTO practice_log (user_text, correction) VALUES (?, ?)", (user_text, correction))
    conn.commit()

def get_practice_count(conn):
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM practice_log")
    return c.fetchone()[0]

# --- FUNCIONES DE AUDIO ---
def transcribe_audio(audio_bytes):
    r = sr.Recognizer()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    try:
        with sr.AudioFile(temp_audio_path) as source:
            audio_data = r.record(source)
            text = r.recognize_google(audio_data, language="en-US")
            return text
    except sr.UnknownValueError:
        return "No se pudo entender el audio. Intenta hablar más claro."
    except Exception as e:
        return f"Error al procesar el audio: {e}"
    finally:
        os.remove(temp_audio_path)

def generate_tts(text):
    tts = gTTS(text=text, lang='en', slow=False)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        tts.save(temp_audio.name)
        return temp_audio.name

# --- INICIALIZACIÓN ---
conn = init_db()

# --- SIDEBAR: PANEL DE CONTROL ---
with st.sidebar:
    st.header("📊 Tu Progreso")
    total_practices = get_practice_count(conn)
    st.metric(label="Prácticas Totales", value=total_practices)
    
    st.divider()
    st.subheader("📚 Historial de Prácticas")
    if st.button("Cargar historial", use_container_width=True):
        df = pd.read_sql_query("SELECT timestamp as Fecha, user_text as Frase FROM practice_log ORDER BY timestamp DESC", conn)
        st.dataframe(df, hide_index=True, use_container_width=True)

# --- ÁREA PRINCIPAL ---
st.title("⚡ Tutor de Pronunciación Pro")
st.markdown("Mejora tu fluidez en inglés. Graba tu voz, valida la transcripción automática y compara con la pronunciación nativa.")
st.write("") # Espaciador

# Dividimos la pantalla en dos columnas
col1, col2 = st.columns([1, 1.2], gap="large")

with col1:
    st.markdown("### 🎙️ 1. Graba tu voz")
    st.info("Habla en inglés de forma clara y natural.")
    
    # EL NUEVO BOTÓN NATIVO DE STREAMLIT (Mucho más pro)
    audio_file = st.audio_input("Haz clic para empezar a grabar")

with col2:
    st.markdown("### ⚙️ 2. Análisis en tiempo real")
    
    if audio_file is not None:
        # Usamos un contenedor con borde para que parezca una "tarjeta" de resultados
        with st.container(border=True):
            with st.spinner("Procesando tu voz..."):
                # st.audio_input devuelve un archivo, usamos .read() para obtener los bytes
                user_text = transcribe_audio(audio_file.read()) 
            
            if user_text and not user_text.startswith("Error") and not user_text.startswith("No se pudo"):
                st.success("¡Transcripción exitosa!")
                
                st.markdown("**El sistema entendió:**")
                st.markdown(f"> *{user_text}*")
                
                st.divider()
                st.markdown("**🎧 Escucha la pronunciación nativa:**")
                audio_tts = generate_tts(user_text) 
                st.audio(audio_tts, format="audio/mp3")
                
                save_to_db(conn, user_text, "Modo Pro")
            else:
                st.error(user_text)
    else:
        # Estado vacío cuando no hay grabación
        with st.container(border=True):
            st.write("Esperando tu grabación...")
            st.caption("El análisis de tu pronunciación aparecerá en este panel.")
