import streamlit as st
import requests
import os

# 1. Page Config
st.set_page_config(page_title="Gemini 2.0 (Fixed)", page_icon="⚡", layout="centered")

# --- Authentication ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def check_login():
    user = st.session_state.get('input_username', '')
    pwd = st.session_state.get('input_password', '')
    try:
        if "credentials" in st.secrets and \
           user == st.secrets["credentials"]["username"] and \
           pwd == st.secrets["credentials"]["password"]:
            st.session_state['logged_in'] = True
        else:
            st.error("Login Failed!")
    except:
        st.error("Secrets Error")

if not st.session_state['logged_in']:
    st.title("🔐 Login")
    st.text_input("Username", key="input_username")
    st.text_input("Password", type="password", key="input_password")
    st.button("Login", on_click=check_login)
    st.stop()

# ==========================================
# Main App
# ==========================================

st.title("⚡ Gemini 2.0 TTS (Auto-Fix)")
st.caption("Automatically finds the correct Model Name for you.")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Selection ---
VOICES = {
    "Puck (Upbeat)": "Puck",
    "Charon (Deep)": "Charon",
    "Zephyr (Bright)": "Zephyr",
    "Fenrir (Excited)": "Fenrir",
    "Aoede (Soft)": "Aoede",
    "Kore (Firm)": "Kore",
}
selected_voice_name = st.selectbox("အသံ (Voice)", list(VOICES.keys()))
selected_voice_id = VOICES[selected_voice_name]

text_input = st.text_area("စာရိုက်ထည့်ပါ (Myanmar / English):", height=200)

# --- Functions ---

def generate_with_auto_model(text, voice_id):
    if "gemini_api_key" not in st.secrets:
        return None, "API Key မရှိပါ! secrets.toml မှာ gemini_api_key ထည့်ပေးပါ။"
    
    api_key = st.secrets["gemini_api_key"]
    url = "https://generativelanguage.googleapis.com/v1beta/openai/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Google က Model နာမည်ခဏခဏပြောင်းလို့ (၃) မျိုးလုံး စမ်းပါမယ်
    POSSIBLE_MODELS = [
        "gemini-2.0-flash-exp",  # အဖြစ်နိုင်ဆုံး (Experimental)
        "gemini-2.0-flash",      # Standard
        "tts-1",                 # Generic OpenAI mapping
        "gemini-1.5-flash"       # Old fallback
    ]
    
    last_error = ""

    # Loop Through Models
    for model in POSSIBLE_MODELS:
        data = {
            "model": model,
            "input": text,
            "voice": voice_id
        }
        
        try:
            # Request ပို့မယ်
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                # အောင်မြင်ရင် Audio နဲ့ အသုံးပြုလိုက်တဲ့ Model နာမည်ကို ပြန်ပို့မယ်
                return response.content, None, model 
            else:
                # 404 ဆိုရင် နောက် model တစ်ခုကို ဆက်စမ်းမယ်
                last_error = f"Model '{model}' failed ({response.status_code})"
                continue 
                
        except Exception as e:
            last_error = str(e)
            continue

    return None, f"All models failed. Last error: {last_error}", None

# --- Generate Logic ---

if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        with st.spinner("Connecting to Gemini AI..."):
            
            # Auto-Model Function ကို ခေါ်မယ်
            audio_content, error, used_model = generate_with_auto_model(
                text_input, 
                selected_voice_id
            )

            if error:
                st.error("အားနာပါတယ်၊ ချိတ်ဆက်မရပါ:")
                st.code(error)
            
            elif audio_content:
                st.success(f"Success! (Used Model: {used_model})") # ဘယ် Model နဲ့ အောင်မြင်လဲ ပြပေးမယ်
                st.audio(audio_content, format="audio/mp3")
                st.download_button("Download MP3", audio_content, "audio.mp3", "audio/mp3")
