"""
CapLine TazzoX - Backend API (Flask)
Handles audio processing, transcription, and translation
"""

from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
import whisper
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer
from gtts import gTTS
import tempfile
import os
import base64

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend
socketio = SocketIO(app, cors_allowed_origins="*")

# ═══════════════════════════════════════════════════════════════════
# LOAD MODELS ON STARTUP
# ═══════════════════════════════════════════════════════════════════

print("Loading AI models...")
whisper_model = whisper.load_model("base")
print("\u2713 Whisper loaded")

m2m_tokenizer = M2M100Tokenizer.from_pretrained("facebook/m2m100_418M")
m2m_model = M2M100ForConditionalGeneration.from_pretrained("facebook/m2m100_418M")
print("\u2713 Translation model loaded")

# In-memory session store for real-time multi-party conversations
# Structure:
# SESSIONS = {
#   session_id: {
#       "participants": { speaker_id: {"target_lang": "hi", "display_name": "User"} },
#       "history": [ ... utterance dicts ... ]
#   }
# }
SESSIONS = {}

# ═══════════════════════════════════════════════════════════════════
# LANGUAGE MAPPINGS
# ═══════════════════════════════════════════════════════════════════

LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Portuguese": "pt",
    "Russian": "ru",
    "Arabic": "ar",
    "Turkish": "tr",
    "Chinese": "zh-CN",
    "Bengali": "bn",
    "Telugu": "te",
    "Marathi": "mr",
    "Tamil": "ta",
    "Gujarati": "gu",
    "Kannada": "kn",
    "Urdu": "ur",
    "Malay": "ms",
    "Indonesian": "id"
}

# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def translate_text(text, src_lang, tgt_lang):
    """Translate text using M2M100"""
    if not text.strip():
        return text
    
    try:
        m2m_tokenizer.src_lang = src_lang
        encoded = m2m_tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        generated = m2m_model.generate(
            **encoded,
            forced_bos_token_id=m2m_tokenizer.get_lang_id(tgt_lang),
            max_length=512
        )
        return m2m_tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
    except Exception as e:
        print(f"Translation error: {e}")
        return text


# ═══════════════════════════════════════════════════════════════════
# REAL-TIME STREAMING: SOCKET.IO EVENTS
# ═══════════════════════════════════════════════════════════════════


@socketio.on('join_session')
def handle_join_session(data):
    session_id = data.get('session_id')
    speaker_id = data.get('speaker_id')
    target_language = data.get('target_language', 'Hindi')
    display_name = data.get('display_name', speaker_id)

    if not session_id or not speaker_id:
        emit('error', {'message': 'session_id and speaker_id are required'})
        return

    join_room(session_id)

    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "participants": {},
            "history": []
        }

    SESSIONS[session_id]["participants"][speaker_id] = {
        "target_language": target_language,
        "display_name": display_name
    }

    emit('session_joined', {
        'session_id': session_id,
        'speaker_id': speaker_id,
        'target_language': target_language,
        'display_name': display_name
    })

    emit('participant_update', {
        'session_id': session_id,
        'participants': SESSIONS[session_id]["participants"],
    }, room=session_id)


@socketio.on('leave_session')
def handle_leave_session(data):
    session_id = data.get('session_id')
    speaker_id = data.get('speaker_id')

    if not session_id or not speaker_id:
        emit('error', {'message': 'session_id and speaker_id are required'})
        return

    leave_room(session_id)

    if session_id in SESSIONS and speaker_id in SESSIONS[session_id]["participants"]:
        del SESSIONS[session_id]["participants"][speaker_id]

        emit('participant_update', {
            'session_id': session_id,
            'participants': SESSIONS[session_id]["participants"],
        }, room=session_id)


@socketio.on('audio_chunk')
def handle_audio_chunk(data):
    session_id = data.get('session_id')
    speaker_id = data.get('speaker_id')
    audio_b64 = data.get('audio_base64')
    target_language = data.get('target_language')
    mime_type = data.get('mime_type') or ''

    if not session_id or not speaker_id or not audio_b64:
        emit('error', {'message': 'session_id, speaker_id, audio_base64 are required'})
        return

    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "participants": {},
            "history": []
        }

    if not target_language:
        # default to participant setting or Hindi
        participant = SESSIONS[session_id]["participants"].get(speaker_id, {})
        target_language = participant.get('target_language', 'Hindi')

    target_code = LANGUAGES.get(target_language, 'hi')

    # Choose file extension based on mime_type hint
    ext = '.webm'
    mt = mime_type.lower()
    if 'ogg' in mt:
        ext = '.ogg'
    elif 'mpeg' in mt or 'mp4' in mt or 'aac' in mt:
        ext = '.m4a'

    # Decode audio chunk to temp file for Whisper/FFmpeg
    try:
        audio_bytes = base64.b64decode(audio_b64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as f:
            audio_path = f.name
            f.write(audio_bytes)

        # Skip extremely small chunks that FFmpeg/Whisper can't handle
        if os.path.getsize(audio_path) < 4000:  # ~a few ms of audio
            os.remove(audio_path)
            return

        # Transcribe chunk
        try:
            result = whisper_model.transcribe(audio_path)
        except Exception as asr_err:
            print(f"Real-time ASR error: {asr_err}")
            os.remove(audio_path)
            return

        input_text = result.get("text", "").strip()
        src_lang = result.get("language", "en")

        # If user specified their spoken language, override detected language
        if source_language:
            src_override = LANGUAGES.get(source_language, None)
            if src_override:
                src_lang = src_override

        os.remove(audio_path)

        if not input_text:
            return

        # Translate
        translated_text = translate_text(input_text, src_lang, target_code)

        # Optionally synthesize TTS for the translated chunk
        audio_chunk_b64 = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
                tts_path = f.name

            tts = gTTS(text=translated_text, lang=target_code, slow=False)
            tts.save(tts_path)

            with open(tts_path, 'rb') as f:
                audio_chunk_b64 = base64.b64encode(f.read()).decode('utf-8')

            os.remove(tts_path)
        except Exception as e:
            print(f"Real-time TTS error: {e}")

        event = {
            'session_id': session_id,
            'speaker_id': speaker_id,
            'input_text': input_text,
            'input_language': src_lang,
            'translated_text': translated_text,
            'target_language': target_language,
            'audio_base64': audio_chunk_b64,
        }

        # Append to session history
        SESSIONS[session_id]["history"].append(event)

        # Broadcast to everyone in the session room
        emit('translation_result', event, room=session_id)

    except Exception as e:
        print(f"Real-time audio_chunk error: {e}")
        emit('error', {'message': str(e)})

# ═══════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "status": "online",
        "service": "CapLine TazzoX API",
        "version": "1.0"
    })


@app.route('/dashboard')
def dashboard():
    return render_template('rt_dashboard.html')

@app.route('/languages', methods=['GET'])
def get_languages():
    """Get list of supported languages"""
    return jsonify({
        "languages": sorted(LANGUAGES.keys())
    })

@app.route('/translate', methods=['POST'])
def translate_audio():
    """
    Main translation endpoint
    Expects: audio file + target language
    Returns: transcription + translation + audio
    """
    
    try:
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        target_language = request.form.get('target_language', 'Hindi')
        source_language = request.form.get('source_language')
        
        # Get language code
        target_code = LANGUAGES.get(target_language, "hi")
        
        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as f:
            audio_path = f.name
            audio_file.save(audio_path)
        
        # Step 1: Transcribe with Whisper
        print(f"Transcribing audio...")
        result = whisper_model.transcribe(audio_path)
        input_text = result.get("text", "").strip()
        src_lang = result.get("language", "en")
        
        if not input_text:
            os.remove(audio_path)
            return jsonify({"error": "No speech detected"}), 400
        
        print(f"Input: {input_text}")
        
        # Step 2: Translate
        print(f"Translating to {target_language}...")
        translated_text = translate_text(input_text, src_lang, target_code)
        print(f"Translation: {translated_text}")
        
        # Step 3: Generate TTS
        print(f"Generating speech...")
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            tts_path = f.name
        
        tts = gTTS(text=translated_text, lang=target_code, slow=False)
        tts.save(tts_path)
        
        # Read audio file and encode to base64
        with open(tts_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode('utf-8')
        
        # Cleanup
        os.remove(audio_path)
        os.remove(tts_path)
        
        # Return response
        return jsonify({
            "success": True,
            "input_text": input_text,
            "input_language": src_lang,
            "translated_text": translated_text,
            "target_language": target_language,
            "audio_base64": audio_data
        })
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════════════════════════════════════
# RUN SERVER
# ═══════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("\n" + "="*60)
    print("CapLine TazzoX Backend Server")
    print("="*60)
    print("Server starting on http://localhost:5000")
    print("="*60 + "\n")

    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
