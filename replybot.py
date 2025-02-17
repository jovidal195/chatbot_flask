from flask import Flask, request, jsonify
import requests
import urllib.parse
from flask_cors import CORS
from pydub import AudioSegment
import speech_recognition as sr
import markdown
import tempfile
import base64
from gtts import gTTS
import os

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


def markdown_to_html(markdown_text):
    # Convertir le texte Markdown en HTML
    html_content = markdown.markdown(markdown_text)
    html_content = html_content.replace('<a href="', '<a target="_blank" href="')
    return html_content

@app.route("/generate", methods=["POST"])
def generate_text():
    API_URL = "https://text.pollinations.ai/"

    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing 'message' parameter"}), 400
    
    prompt = data["message"]
    model = data.get("model", "llama")  # Modèle par défaut : openai
    seed = data.get("seed")
    json_mode = data.get("json", "true")
    instructions = ""
    try:
        system = "à date ceci à été dit :" + data["system"]
    except Exception as e:
        print(str(e))
        system = "à date ceci à été dit :" 
    system = instructions + system
    try:
        voice = data["voice"]
    except Exception as e:
        voice = False
    private = data.get("private", "false")
    
    encoded_prompt = urllib.parse.quote(prompt)
    query_url = f"{API_URL}{encoded_prompt}?model={model}&json={json_mode}&private={private}"
    if seed:
        query_url += f"&seed={seed}"
    if system:
        encoded_system = urllib.parse.quote(system)
        query_url += f"&system={encoded_system}"
    
    response = requests.get(query_url)
    try :
        answer = response.text
    except:
        answer = "Pas de réponse"
    
    answer_html = markdown_to_html(answer)
    
    response_data = {"reply": answer_html}
    
    # Génération de la voix si demandé
    if voice:
        try:
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            temp_audio_path = temp_audio.name
            temp_audio.close()  # Fermer le fichier pour permettre à gTTS de l'utiliser
            
            tts = gTTS(text=answer, lang='fr-ca')
            tts.save(temp_audio_path)
            
            # Encodage en base64
            with open(temp_audio_path, "rb") as audio:
                audio_base64 = base64.b64encode(audio.read()).decode('utf-8')
            
            response_data["audio"] = audio_base64
        except Exception as e:
            response_data["audio_error"] = str(e)
        finally:
            os.remove(temp_audio_path)  # Suppression du fichier après utilisation
    
    if response.status_code == 200:
        return jsonify(response_data)
    else:
        return jsonify({"error": "Failed to fetch response", "status_code": response.status_code}), response.status_code
        
@app.route('/r', methods=['POST'])
def r():
    
    audio_file = request.files['audio']
    r_instance = sr.Recognizer()
    # Créez un fichier temporaire avec une extension explicite
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
        temp_audio_path = temp_audio.name
    # Conversion du fichier audio
    audio = AudioSegment.from_file(audio_file)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(temp_audio_path, format="wav")
    
    with sr.AudioFile(temp_audio_path) as source:
        audio_data = r_instance.record(source)
        text = r_instance.recognize_google(audio_data, language="fr-CA")
    return jsonify(reply=text), 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5004, debug=True)