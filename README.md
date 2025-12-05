# CapLine(TazzoX)-V1

Enhanced multi‑party speech translation prototype with a dark, animated dashboard.

- **Backend:** Flask + Flask-SocketIO (only used for future realtime), Whisper ASR, M2M100 translation, gTTS TTS
- **Frontend:** Simple HTML/CSS/JS dashboard served by Flask (`/dashboard`)
- **Mode:** Single‑user, single target language per session (record → translate → play translated audio)

---

## Features

- Record microphone audio directly from the browser
- Choose **your spoken language** and **target language**
- Whisper transcribes the audio
- M2M100 translates the transcription
- gTTS generates translated speech
- Dashboard shows:
  - Translated text in a glassmorphism panel
  - Audio player with the translated voice
  - Animated orb visualizer on a dark background

Supported language names (mapped in `LANGUAGES` in `app.py`):

- English, Hindi, Bengali, Spanish, French, German, Japanese
- Turkish, Arabic, Portuguese

You can easily extend this by adding more entries to `LANGUAGES` and the dropdowns in `templates/rt_dashboard.html`.

---

## Project structure

```text
backend/
├── app.py                    # Flask backend, Whisper + translation + TTS
├── requirements.txt          # Python dependencies
├── templates/
│   ├── dashboard.html        # Original simple dashboard (not used now)
│   └── rt_dashboard.html     # Dark themed recording dashboard (main UI)
└── static/
    └── visualizer.gif        # Animated orb / visualizer (add this yourself)
```

---

## Setup

### 1. Create and activate virtualenv (recommended)

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

If `torch` or `whisper` has trouble installing on your machine, install them separately following PyTorch’s official instructions for your OS/CPU/GPU.

### 3. (macOS) Fix SSL certificates if Whisper download fails

If you see a `CERTIFICATE_VERIFY_FAILED` error when Whisper downloads its model, run the Python “Install Certificates” command for your version, for example:

```bash
open "/Applications/Python 3.13/Install Certificates.command"
```

Then re‑activate the venv and run the app again.

---

## Running the backend

From `backend/` with the virtualenv activated:

```bash
python app.py
```

You should see logs like:

```text
✓ Whisper loaded
✓ Translation model loaded
CapLine TazzoX Backend Server
Server starting on http://localhost:5000
```

The server runs on `http://localhost:5000`.

Health check:

```text
GET http://localhost:5000/
```

returns JSON status.

---

## Using the dark dashboard

1. Ensure the backend is running (`python app.py`).
2. Place your animated GIF at:

   ```text
   backend/static/visualizer.gif
   ```

3. Open the dashboard in your browser:

   ```text
   http://localhost:5000/dashboard
   ```

4. In the left control panel:
   - Set **Session ID** (any string, e.g. `room-1`).
   - Set **Your Name / ID**.
   - Choose **Your Language (You Speak)**.
   - Choose **Target Language**.

5. Click **Connect & Start Mic** and allow microphone access.
6. Speak your sentence or paragraph.
7. Click **Stop**.

The backend will:

1. Receive the recorded audio
2. Transcribe it with Whisper
3. Translate text with M2M100
4. Generate translated speech with gTTS

The dashboard then:

- Shows the translated text in the bottom bar
- Loads the translated audio into the player and attempts to auto‑play it
- If autoplay is blocked by the browser, you can click the play button manually

---

## Notes on realtime streaming

There is a Socket.IO based `audio_chunk` handler in `app.py` designed for future **true realtime** (chunked) streaming. For stability on macOS and cross‑browser audio formats, the current UI uses a simpler **record → send → translate** pattern instead.

If you later want to experiment with realtime:

- Implement a WebSocket/Socket.IO client that sends properly encoded chunks.
- Use the `handle_audio_chunk` event in `app.py`.

For now, the main supported and tested path is the `/translate` HTTP endpoint used by `rt_dashboard.html`.

---

## Git / repo notes

- Repo: `CapLine_TazzoX_V1`
- Default branch: `main`
- To commit new changes:

```bash
git add .
git commit -m "Describe your change"
git push
```

---

## Roadmap ideas

- Multi‑party sessions with separate target languages per participant (using Socket.IO rooms).
- Live subtitles while speaking (smaller audio chunks pushed over WebSocket).
- Conversation memory and context visualization (using the graph / prosody code from experiments).
- More polished front‑end (React/Tailwind or similar) using this backend as an API.
