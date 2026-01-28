import streamlit as st
import requests
import os

# 1. Page Config
st.set_page_config(page_title="Gemini 2.0 Only", page_icon="⚡", layout="centered")

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

st.title("⚡ Gemini 2.0 TTS (Pure)")
st.caption("Direct connection to AI Studio (No Edge TTS)")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Configuration ---

# 1. Models (404 Error တက်ရင် Model ပြောင်းစမ်းလို့ရအောင် ထည့်ပေးထားပါတယ်)
MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-exp"]
selected_model = st.selectbox("Model", MODELS)

# 2. Voices (AI Studio Voices)
VOICES = {
    "Puck (Upbeat)": "Puck",
    "Charon (Deep)": "Charon",
    "Zephyr (Bright)": "Zephyr",
    "Fenrir (Excited)": "Fenrir",
    "Aoede (Soft)": "Aoede",
    "Kore (Firm)": "Kore",
}
selected_voice_name = st.selectbox("Voice", list(VOICES.keys()))
selected_voice_id = VOICES[selected_voice_name]

text_input = st.text_area("စာရိုက်ထည့်ပါ (Myanmar / English):", height=200)

# --- Functions ---

def generate_gemini_audio(text, voice_id, model_name):
    # 1. API Key Check
    if "gemini_api_key" not in st.secrets:
        return None, "API Key မရှိပါ! secrets.toml မှာ gemini_api_key ထည့်ပေးပါ။"
    
    api_key = st.secrets["gemini_api_key"]
    
    # 2. Endpoint (OpenAI Compatible)
    url = "https://generativelanguage.googleapis.com/v1beta/openai/audio/speech"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": model_name,
        "input": text,
        "voice": voice_id,
        "response_format": "mp3"
    }
    
    try:
        # 3. Request
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            return response.content, None
        else:
            # Error Detail
            return None, f"Error {response.status_code}: {response.text}"
            
    except Exception as e:
        return None, str(e)

# --- Generate Logic ---

if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        with st.spinner(f"Gemini ({selected_voice_id}) is reading..."):
            
            audio_content, error = generate_gemini_audio(
                text_input, 
                selected_voice_id,
                selected_model
            )

            if error:
                st.error("အဆင်မပြေပါ:")
                st.code(error) # Error အတိအကျကို ပြပေးပါမယ်
                
                # 404 အကြံပြုချက်
                if "404" in str(error):
                    st.info("💡 Tip: 'Model' နေရာမှာ 'gemini-2.0-flash-exp' ကို ပြောင်းရွေးပြီး ပြန်စမ်းကြည့်ပါ။")
            
            elif audio_content:
                st.success("Success!")
                st.audio(audio_content, format="audio/mp3")
                st.download_button("Download MP3", audio_content, "audio.mp3", "audio/mp3")
