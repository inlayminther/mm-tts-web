import streamlit as st
import edge_tts
import asyncio
import tempfile
import os

# 1. Page Config (ဒါက အမြဲတမ်း ထိပ်ဆုံးမှာ ရှိရပါမယ်)
st.set_page_config(page_title="Secure TTS App", page_icon="🔐", layout="centered")

# --- Authentication Logic (Login စနစ်) ---

# Session State စစ်ဆေးခြင်း
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login():
    user = st.session_state.get('input_username', '')
    pwd = st.session_state.get('input_password', '')
    
    # st.secrets မှ password နှင့် တိုက်စစ်ခြင်း
    try:
        # Credentials ရှိမရှိ အရင်စစ်မယ်
        if "credentials" in st.secrets and \
           user == st.secrets["credentials"]["username"] and \
           pwd == st.secrets["credentials"]["password"]:
            st.session_state['logged_in'] = True
        else:
            st.error("Username သို့မဟုတ် Password မှားယွင်းနေပါတယ်!")
    except Exception as e:
        st.error(f"Error: {e}. Secrets မသတ်မှတ်ရသေးပါ (Please configure st.secrets)")

# Login မဝင်ရသေးရင် Login Form ပြမယ်
if not st.session_state['logged_in']:
    st.title("🔐 Login")
    st.text_input("Username", key="input_username")
    st.text_input("Password", type="password", key="input_password")
    st.button("Login", on_click=check_login)
    st.stop()  # Login မဝင်မချင်း အောက်က ကုဒ်တွေကို မ run ပါဘူး

# ==========================================
# Login ဝင်ပြီးမှ မြင်ရမယ့် Main App (TTS Code)
# ==========================================

st.title("🗣️ Multi-Language Text-to-Speech")

# User Greeting
try:
    username_display = st.secrets['credentials']['username']
except:
    username_display = "User"
st.success(f"Welcome, {username_display}!")

# Logout Button
if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- TTS Logic (မူရင်းကုဒ်အတိုင်း) ---
if 'audio_data' not in st.session_state:
    st.session_state['audio_data'] = None

# Voice Data
VOICE_DATA = {
    "မြန်မာ (Myanmar)": {"Male (Thiha)": "my-MM-ThihaNeural", "Female (Nilar)": "my-MM-NilarNeural"},
    "အင်္ဂလိပ် (English - US)": {"Female (Aria)": "en-US-AriaNeural", "Male (Christopher)": "en-US-ChristopherNeural"},
    "အင်္ဂလိပ် (English - UK)": {"Female (Sonia)": "en-GB-SoniaNeural", "Male (Ryan)": "en-GB-RyanNeural"}
}

st.subheader("Settings")
selected_language = st.selectbox("ဘာသာစကား (Language)", list(VOICE_DATA.keys()))
voice_options = VOICE_DATA[selected_language]
selected_voice_label = st.selectbox("အသံ (Voice)", list(voice_options.keys()))
selected_voice = voice_options[selected_voice_label]
speed = st.slider("Speed", 0.5, 2.0, 1.0, 0.1)

def get_rate_string(speed_val):
    if speed_val == 1.0: return "+0%"
    pct = int((speed_val - 1) * 100)
    return f"+{pct}%" if pct >= 0 else f"{pct}%"

text_input = st.text_area("စာရိုက်ထည့်ပါ:", height=150)

async def generate_tts(text, voice, rate):
    communicate = edge_tts.Communicate(text, voice, rate=rate) if rate != "+0%" else edge_tts.Communicate(text, voice)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        tmp_path = tmp_file.name
    await communicate.save(tmp_path)
    return tmp_path

if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        with st.spinner("Processing..."):
            try:
                temp_path = asyncio.run(generate_tts(text_input, selected_voice, get_rate_string(speed)))
                with open(temp_path, "rb") as f:
                    st.session_state['audio_data'] = f.read()
                os.remove(temp_path)
            except Exception as e:
                st.error(f"Error: {e}")

# --- Result & Download Section ---
if st.session_state['audio_data']:
    st.markdown("---")
    st.success("အသံဖိုင် ရပါပြီ!")
    
    # Audio Player
    st.audio(st.session_state['audio_data'], format="audio/mp3")
    
    # Download Button (ဒီခလုတ်ကမှ .mp3 နဲ့ အမှန် ဒေါင်းပေးမှာပါ)
    st.download_button(
        label="Download MP3 File",
        data=st.session_state['audio_data'],
        file_name="tts_audio.mp3",
        mime="audio/mp3"
    )
