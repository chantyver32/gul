import streamlit as st
import sqlite3
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os
import pandas as pd
import random
from difflib import SequenceMatcher

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="English Tutor Pro", page_icon="⚡", layout="wide")

# --- SISTEMA DE PUNTOS Y GAMIFICACIÓN (En Memoria) ---
if 'xp' not in st.session_state:
    st.session_state.xp = 0
if 'current_challenge' not in st.session_state:
    st.session_state.current_challenge = "Welcome to your English practice."

# Frases estratégicas para practicar
CHALLENGES = [
    "We need to optimize our inventory process.",
    "Can you send me the sales report by tomorrow?",
    "Only the last one standing will take the victory.",
    "The customer service team is doing a great job.",
    "I am learning how to build web applications."
]

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

# --- FUNCIONES DE AUDIO Y ANÁLISIS ---
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
        return "No se pudo entender. Intenta hablar más fuerte."
    except Exception as e:
        return f"Error: {e}"
    finally:
        os.remove(temp_audio_path)

def generate_tts(text):
    tts = gTTS(text=text, lang='en', slow=False)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        tts.save(temp_audio.name)
        return temp_audio.name

# Compara la similitud de los textos para dar una calificación
def calculate_accuracy(target, spoken):
    target_clean = target.lower().replace(".", "").replace("?", "").replace(",", "")
    spoken_clean = spoken.lower().replace(".", "").replace("?", "").replace(",", "")
    ratio = SequenceMatcher(None, target_clean, spoken_clean).ratio()
    return int(ratio * 100)

# --- UI: INTERFAZ PRINCIPAL ---
conn = init_db()

# Barra lateral rediseñada con perfiles
with st.sidebar:
    st.header("🎮 Tu Perfil")
    
    # Lógica de rangos
    if st.session_state.xp < 100:
        nivel = "Bronce 🥉"
    elif st.session_state.xp < 300:
        nivel = "Plata 🥈"
    else:
        nivel = "Oro 🥇"
        
    st.metric(label="Rango Actual", value=nivel)
    st.metric(label="Experiencia (XP)", value=f"{st.session_state.xp} XP")
    
    st.divider()
    st.subheader("📊 Estadísticas Globales")
    st.metric(label="Prácticas Históricas", value=get_practice_count(conn))
    
    if st.button("Ver historial detallado", use_container_width=True):
        df = pd.read_sql_query("SELECT timestamp as Fecha, user_text as Frase, correction as Detalles FROM practice_log ORDER BY timestamp DESC", conn)
        st.dataframe(df, hide_index=True, use_container_width=True)

st.title("⚡ Tutor de Pronunciación Pro")
st.write("Gana experiencia (XP) superando retos de pronunciación.")

# CREAMOS LAS PESTAÑAS (TABS)
tab1, tab2 = st.tabs(["🎯 Modo Reto (Calificado)", "🎙️ Modo Libre"])

# PESTAÑA 1: MODO RETO
with tab1:
    col1, col2 = st.columns([1, 1.2], gap="large")
    
    with col1:
        st.markdown("### 1. Lee esta frase en voz alta")
        st.info(f"**{st.session_state.current_challenge}**")
        
        if st.button("🔄 Cambiar frase (Skip)"):
            st.session_state.current_challenge = random.choice(CHALLENGES)
            st.rerun()
            
        audio_reto = st.audio_input("Graba tu lectura aquí", key="reto")
        
    with col2:
        st.markdown("### 2. Resultados de Precisión")
        if audio_reto:
            with st.container(border=True):
                with st.spinner("Evaluando tu pronunciación..."):
                    transcription = transcribe_audio(audio_reto.read())
                    
                if transcription and not transcription.startswith("Error") and not transcription.startswith("No se"):
                    accuracy = calculate_accuracy(st.session_state.current_challenge, transcription)
                    
                    st.markdown("**Lo que la IA escuchó:**")
                    st.write(f"> *{transcription}*")
                    
                    # Barra visual de porcentaje
                    st.progress(accuracy / 100)
                    
                    # Sistema de recompensas
                    if accuracy >= 85:
                        st.success(f"¡Excelente pronunciación! Precisión: {accuracy}% (+50 XP)")
                        st.session_state.xp += 50
                        st.balloons() # Animación pro
                    elif accuracy >= 60:
                        st.warning(f"Buen intento, pero puede mejorar. Precisión: {accuracy}% (+20 XP)")
                        st.session_state.xp += 20
                    else:
                        st.error(f"Hay que practicar más esta frase. Precisión: {accuracy}% (+5 XP)")
                        st.session_state.xp += 5
                        
                    st.markdown("**🎧 Escucha cómo la diría un nativo:**")
                    audio_tts = generate_tts(st.session_state.current_challenge)
                    st.audio(audio_tts, format="audio/mp3")
                    
                    save_to_db(conn, transcription, f"Reto de Precisión: {accuracy}%")
                else:
                    st.error(transcription)

# PESTAÑA 2: MODO LIBRE
with tab2:
    col_free1, col_free2 = st.columns([1, 1.2], gap="large")
    
    with col_free1:
        st.markdown("### 🎙️ Práctica Abierta")
        st.write("Di cualquier cosa en inglés para ver si el sistema te entiende.")
        audio_libre = st.audio_input("Graba lo que quieras", key="libre")
    
    with col_free2:
        st.markdown("### ⚙️ Transcripción")
        if audio_libre:
            with st.container(border=True):
                with st.spinner("Procesando..."):
                    user_text = transcribe_audio(audio_libre.read()) 
                    
                if user_text and not user_text.startswith("Error") and not user_text.startswith("No se"):
                    st.success("¡El sistema te entendió perfecto! (+10 XP)")
                    st.session_state.xp += 10
                    st.markdown(f"> *{user_text}*")
                    
                    audio_tts = generate_tts(user_text) 
                    st.audio(audio_tts, format="audio/mp3")
                    save_to_db(conn, user_text, "Modo Libre")
                else:
                    st.error(user_text)
