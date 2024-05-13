from flask import Flask, request, jsonify
import os
from get_docker_secret import get_docker_secret
from bot import BotFactory

app = Flask(__name__, static_url_path='')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

TELEGRAM_TOKEN = get_docker_secret('telegram_bot_token')
if TELEGRAM_TOKEN is None:
    raise ValueError("Token is not available")

TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']

bot_factory = BotFactory(TELEGRAM_TOKEN, TELEGRAM_APP_URL)

@app.route('/', methods=['GET'])
def index():
    return 'Ok', 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "Service is up and running!"}), 200

@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    if "message" in req:
        msg = req['message']
    elif "edited_message" in req:
        msg = req['edited_message']
    else:
        return 'No message', 400

    bot = bot_factory.get_bot(msg)
    bot.handle_message(msg)
    return 'Ok', 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8443)
