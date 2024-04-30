from flask import Flask, request, jsonify
import os
from bot import BotFactory

app = Flask(__name__, static_url_path='')
app.config['UPLOAD_FOLDER'] = 'static/uploads'

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_APP_URL = os.environ['TELEGRAM_APP_URL']

@app.route('/', methods=['GET'])
def index():
    return 'Ok', 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "Service is up and running!"}), 200

@app.route(f'/{TELEGRAM_TOKEN}/', methods=['POST'])
def webhook():
    req = request.get_json()
    msg = req['message']
    bot = bot_factory.get_bot(msg)
    bot.handle_message(msg)
    return 'Ok'


if __name__ == "__main__":
    bot_factory = BotFactory(TELEGRAM_TOKEN, TELEGRAM_APP_URL)

    app.run(host='0.0.0.0', port=8443)
