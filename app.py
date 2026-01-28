import streamlit as st
import requests
import base64
import os

# 1. Page Config
st.set_page_config(page_title="Gemini Smart TTS", page_icon="🧠", layout="centered")

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

st.title("🧠 Gemini Smart TTS")
st.caption("Converts Myanmar Text -> Phonetics -> Audio (100% Works)")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Selection (Journey Voices) ---
VOICES = {
    "Puck Style (Expressive)": {"id": "en-US-Journey-F", "gender": "FEMALE"},
    "Charon Style (Deep)": {"id": "en-US-Journey-D", "gender": "MALE"},
    "Soft Style": {"id": "en-US-Journey-O", "gender": "FEMALE"},
}
selected_voice_name = st.selectbox("အသံ (Voice)", list(VOICES.keys()))
selected_voice_id = VOICES[selected_voice_name]["id"]

text_input = st.text_area("စာရိုက်ထည့်ပါ (မြန်မာလို ရိုက်နိုင်ပါသည်):", height=200)

# --- Functions ---

# STEP 1: The Brain (Gemini 1.5 Flash)
# မြန်မာစာကို အသံထွက် (Burglish) ပြောင်းပေးမယ့် Function
def get_phonetic_script(original_text, api_key):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Prompt: မြန်မာစာကို အသံထွက်အတိုင်း English လိုရေးခိုင်းခြင်း
    prompt = f"""
    You are a professional transliteration engine. 
    Convert the following Myanmar text into Romanized English phonetics (Burglish) exactly as it sounds when spoken.
    Do not translate the meaning. Only output the pronunciation.
    Example: "မင်္ဂလာပါ" -> "Min Ga Lar Par"
    Example: "နေကောင်းလား" -> "Nay Kaung Lar"
    
    Input Text: {original_text}
    """
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            # Gemini ရဲ့ အဖြေကို ပြန်ယူခြင်း
            phonetic_text = result['candidates'][0]['content']['parts'][0]['text']
            return phonetic_text.strip(), None
        else:
            return None, f"Gemini Brain Error: {response.text}"
    except Exception as e:
        return None, str(e)

# STEP 2: The Mouth (Google Cloud TTS)
# Burglish ကို အသံဖတ်ပေးမယ့် Function
def generate_audio_from_phonetics(phonetic_text, voice_id, api_key):
    url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "input": {"text": phonetic_text},
        "voice": {
            "languageCode": "en-US", # English AI ကို သုံးမယ်
            "name": voice_id
        },
        "audioConfig": {"audioEncoding": "MP3"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            response_json = response.json()
            audio_content = base64.b64decode(response_json['audioContent'])
            return audio_content, None
        else:
            return None, f"TTS Audio Error: {response.text}"
    except Exception as e:
        return None, str(e)

# --- Generate Logic ---

if st.button("Generate Audio", type="primary"):
    if not text_input.strip():
        st.warning("စာရိုက်ထည့်ပါ")
    else:
        api_key = st.secrets.get("gemini_api_key")
        if not api_key:
            st.error("API Key မရှိပါ")
            st.stop()

        with st.spinner("🧠 Gemini is reading (Converting to phonetics)..."):
            
            # Step 1: Convert to Burglish
            phonetic_text, err1 = get_phonetic_script(text_input, api_key)
            
            if err1:
                st.error("Text Conversion Failed:")
                st.code(err1)
            else:
                # Debug: အသံထွက်ပြောင်းထားတာကို ပြပေးမယ် (User သိအောင်)
                st.info(f"🔤 Phonetic: {phonetic_text}")
                
                with st.spinner("🗣️ Generating Voice..."):
                    # Step 2: Speak it out
                    audio_content, err2 = generate_audio_from_phonetics(phonetic_text, selected_voice_id, api_key)
                    
                    if err2:
                        st.error("Audio Generation Failed:")
                        st.code(err2)
                    elif audio_content:
                        st.success("Success!")
                        st.audio(audio_content, format="audio/mp3")
                        st.download_button("Download MP3", audio_content, "audio.mp3", "audio/mp3")
