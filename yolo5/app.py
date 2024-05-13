from flask import Flask, request, jsonify
import uuid
from yolo_utils import identify, write_to_db

app = Flask(__name__, static_url_path='')

@app.route('/', methods=['GET'])
def index():
    return 'Ok'

@app.route('/predict', methods=['POST'])
def predict():
    # Generates a UUID for this current prediction HTTP request. This id can be used as a reference in logs to identify and track individual prediction requests.
    prediction_id = str(uuid.uuid4())

    # Receives a URL parameter representing the image to download from S3
    img_name = request.args.get('imgName')

    # Execute the identification process on the image
    response = identify(img_name, prediction_id)

    if response[1] == 200:
        response = write_to_db(prediction_id, response[0])

    return jsonify(response[0]), response[1]

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081)
