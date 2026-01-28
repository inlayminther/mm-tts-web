import streamlit as st
import requests
import base64
import os

# 1. Page Config
st.set_page_config(page_title="Gemini Smart TTS (Fixed)", page_icon="🧠", layout="centered")

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

st.title("🧠 Gemini Smart TTS (Auto-Fix)")
st.caption("Auto-detects working models. No more 404 errors.")

if st.button("Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# --- Voice Selection ---
VOICES = {
    "Puck Style (Expressive)": {"id": "en-US-Journey-F", "gender": "FEMALE"},
    "Charon Style (Deep)": {"id": "en-US-Journey-D", "gender": "MALE"},
    "Soft Style": {"id": "en-US-Journey-O", "gender": "FEMALE"},
    "Classic Male": {"id": "en-US-Standard-D", "gender": "MALE"},
    "Classic Female": {"id": "en-US-Standard-F", "gender": "FEMALE"},
}
selected_voice_name = st.selectbox("အသံ (Voice)", list(VOICES.keys()))
selected_voice_id = VOICES[selected_voice_name]["id"]

text_input = st.text_area("စာရိုက်ထည့်ပါ (မြန်မာ/English):", height=200)

# --- Functions ---

# STEP 1: The Brain (Robust Model Hunter)
def get_phonetic_script(original_text, api_key):
    # စမ်းသပ်မည့် Model စာရင်း (တစ်ခုမရရင် တစ်ခု ပြောင်းသုံးမည်)
    POSSIBLE_MODELS = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-1.5-pro-001",
        "gemini-pro"
    ]
    
    prompt = f"""
    You are a transliteration engine. 
    Convert this Myanmar text to Romanized English phonetics (Burglish) exactly as it sounds.
    Output ONLY the pronunciation. No explanations.
    Input: {original_text}
    """
    
    data = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    last_error = ""

    # Loop through models until one works
    for model in POSSIBLE_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                try:
                    phonetic_text = result['candidates'][0]['content']['parts'][0]['text']
                    return phonetic_text.strip(), None, model # Return working model name too
                except:
                    # Response format might differ slightly for some models, but usually consistent
                    continue
            else:
                last_error = f"{model}: {response.status_code}"
                continue # Try next model
                
        except Exception as e:
            last_error = str(e)
            continue

    return None, f"All models failed to convert text. Last Error: {last_error}", None

# STEP 2: The Mouth (TTS)
def generate_audio_from_phonetics(phonetic_text, voice_id, api_key):
    url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    data = {
        "input": {"text": phonetic_text},
        "voice": {
            "languageCode": "en-US", 
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
            return None, f"Audio Error: {response.text}"
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

        with st.spinner("Thinking (Auto-detecting Model)..."):
            
            # Step 1: Text -> Phonetics
            phonetic_text, err1, used_model = get_phonetic_script(text_input, api_key)
            
            if err1:
                st.error("Brain Failure:")
                st.write("ဖြစ်နိုင်ခြေများ: API Key တွင် 'Generative Language API' မဖွင့်ရသေးခြင်း သို့မဟုတ် Quota ကုန်ခြင်း။")
                st.code(err1)
            else:
                # Debug Info
                st.success(f"Brain Used: {used_model}") # ဘယ် Model အလုပ်လုပ်သွားလဲ ပြပေးမယ်
                st.info(f"Phonetic: {phonetic_text}")
                
                with st.spinner("Speaking..."):
                    # Step 2: Phonetics -> Audio
                    audio_content, err2 = generate_audio_from_phonetics(phonetic_text, selected_voice_id, api_key)
                    
                    if err2:
                        st.error("Mouth Failure:")
                        st.write("ဖြစ်နိုင်ခြေများ: API Key တွင် 'Cloud Text-to-Speech API' မဖွင့်ရသေးခြင်း။")
                        st.code(err2)
                    elif audio_content:
                        st.audio(audio_content, format="audio/mp3")
                        st.download_button("Download MP3", audio_content, "audio.mp3", "audio/mp3")
