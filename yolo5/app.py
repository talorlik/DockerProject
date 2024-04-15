import time
from pathlib import Path
from flask import Flask, request
from detect import run
import uuid
import yaml
from loguru import logger
import os
from yolo5.yolo_utils import upload_image_to_s3, download_image_from_s3, write_to_db

images_bucket = os.environ['BUCKET_NAME']
images_prefix = os.environ['BUCKET_PREFIX']

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']

app = Flask(__name__)

@app.route('/predict', methods=['POST'])
def predict():
    # Generates a UUID for this current prediction HTTP request. This id can be used as a reference in logs to identify and track individual prediction requests.
    prediction_id = str(uuid.uuid4())

    logger.info(f'Prediction: {prediction_id}. Start processing')

    # Receives a URL parameter representing the image to download from S3
    img_name = request.args.get('imgName')

    if img_name:
        # The bucket name and prefix are provided as env variables BUCKET_NAME and BUCKET_PREFIX respectively.
        original_img_path = images_prefix + "/" + img_name

        if not os.path.exists(images_prefix):
            os.makedirs(images_prefix)

        # Download img_name from S3 and store it to a local path from the original_img_path variable.
        response = download_image_from_s3(images_bucket, original_img_path, original_img_path)

        if response[1] == 200:
            logger.info(f'Prediction: {prediction_id}/{original_img_path}. Download img completed')

            # Predicts the objects in the image
            run(
                weights='yolov5s.pt',
                data='data/coco128.yaml',
                source=original_img_path,
                project='static/data',
                name=prediction_id,
                save_txt=True
            )

            logger.info(f'Prediction: {prediction_id}/{original_img_path}. Done')

            # This is the path for the predicted image with labels
            # The predicted image typically includes bounding boxes drawn around the detected objects, along with class labels and possibly confidence scores.
            predicted_img_path = Path(f'static/data/{prediction_id}/{original_img_path}')

            # Uploads the predicted image (predicted_img_path) to S3.
            response = upload_image_to_s3(images_bucket, original_img_path, predicted_img_path)

            if response[1] == 200:
                logger.info(f'Prediction: {prediction_id}/{original_img_path}. Upload img completed')

                # Parse prediction labels and create a summary
                pred_summary_path = Path(f'static/data/{prediction_id}/labels/{original_img_path.split(".")[0]}.txt')
                if pred_summary_path.exists():
                    with open(pred_summary_path, 'r', encoding="utf-8") as f:
                        labels = f.read().splitlines()
                        labels = [line.split(' ') for line in labels]
                        labels = [{
                            'class': names[int(l[0])],
                            'cx': float(l[1]),
                            'cy': float(l[2]),
                            'width': float(l[3]),
                            'height': float(l[4]),
                        } for l in labels]

                    logger.info(f'Prediction: {prediction_id}/{original_img_path}. Prediction summary:\n\n{labels}')

                    prediction_summary = {
                        'prediction_id': prediction_id,
                        'original_img_path': original_img_path,
                        'predicted_img_path': predicted_img_path,
                        'labels': labels,
                        'time': time.time()
                    }

                    retry = 0
                    curr_exception = None
                    curr_error_code = None
                    while retry < 3:
                        # Store the prediction_summary in MongoDB
                        response = write_to_db(prediction_summary)

                        if response[1] == 200:
                            return prediction_summary, 200
                        else:
                            retry += 1
                            curr_exception = f'Prediction: {prediction_id}/{original_img_path} failed.\n\n{response[0]}'
                            curr_error_code = response[1]
                            logger.exception(f'Prediction: {prediction_id}/{original_img_path} failed.\n\n{response[0]}')

                        time.sleep(3)

                    if retry == 3:
                        return curr_exception, curr_error_code
                else:
                    logger.exception(f'Prediction: {prediction_id}/{original_img_path}. Prediction result not found')
                    return f'Prediction: {prediction_id}/{original_img_path}. Prediction result not found', 404
            else:
                logger.exception(f'Prediction: {prediction_id}/{original_img_path} failed.\n\n{response[0]}')
                return f'Prediction: {prediction_id}/{original_img_path} failed.\n\n{response[0]}', response[1]
        else:
            logger.exception(f'Prediction: {prediction_id}/{original_img_path} failed.\n\n{response[0]}')
            return f'Prediction: {prediction_id}/{original_img_path} failed.\n\n{response[0]}', response[1]
    else:
        logger.exception(f'Prediction: {prediction_id}/{original_img_path}. No image parameter was passed or is empty.')
        return f'Prediction: {prediction_id}/{original_img_path}. No image parameter was passed or is empty.', 500


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081)
