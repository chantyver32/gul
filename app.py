import streamlit as st
import sqlite3
import speech_recognition as sr
from gtts import gTTS
import tempfile
import os
import pandas as pd
from audio_recorder_streamlit import audio_recorder

# --- BASE DE DATOS (SQLite) ---
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

# --- FUNCIONES DE AUDIO ---
def transcribe_audio(audio_bytes):
    r = sr.Recognizer()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    try:
        with sr.AudioFile(temp_audio_path) as source:
            audio_data = r.record(source)
            # Reconoce el audio esperando que hables en inglés
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

# --- INTERFAZ VISUAL ---
st.set_page_config(page_title="Práctica de Inglés", page_icon="🗣️")
st.title("🗣️ Práctica de Pronunciación")
st.write("Graba tu voz en inglés. Si el sistema transcribe correctamente lo que querías decir, ¡tu pronunciación es buena!")

conn = init_db()

audio_bytes = audio_recorder(text="Haz clic en el micrófono para grabar", recording_color="#e83a3a", neutral_color="#6aa36f")

if audio_bytes:
    st.audio(audio_bytes, format="audio/wav")
    
    with st.spinner("Transcribiendo..."):
        user_text = transcribe_audio(audio_bytes)
    
    if user_text and not user_text.startswith("Error") and not user_text.startswith("No se pudo"):
        st.success(f"**El sistema entendió:** {user_text}")
        
        st.markdown("### 🎧 Escucha la pronunciación nativa")
        audio_file = generate_tts(user_text) 
        st.audio(audio_file, format="audio/mp3")
        
        # Guardamos en la base de datos (dejamos un texto por defecto en la columna de corrección)
        save_to_db(conn, user_text, "Modo sin IA - Solo transcripción")
        st.toast("¡Práctica guardada!")
    else:
        st.error(user_text)

st.divider()
st.subheader("📚 Tu Historial")
if st.button("Ver mis prácticas anteriores"):
    df = pd.read_sql_query("SELECT * FROM practice_log ORDER BY timestamp DESC", conn)
    st.dataframe(df, use_container_width=True)
