import time
from pathlib import Path
from detect import run
import boto3
from botocore import exceptions as boto_exceptions
from loguru import logger
from pymongo import MongoClient
from pymongo import errors as mongo_errors
import yaml
import os
from urllib.parse import quote_plus
from get_docker_secret import get_docker_secret
from bson import ObjectId

images_bucket = os.environ['BUCKET_NAME']
images_prefix = os.environ['BUCKET_PREFIX']

aws_profile = os.getenv("AWS_PROFILE", None)
if aws_profile is not None and aws_profile == "dev":
    boto3.setup_default_session(profile_name=aws_profile)

with open("data/coco128.yaml", "r") as stream:
    names = yaml.safe_load(stream)['names']

def convert_objectid(data):
    if isinstance(data, dict):
        return {key: convert_objectid(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_objectid(item) for item in data]
    elif isinstance(data, ObjectId):
        return str(data)  # Convert ObjectId to string
    else:
        return data

def upload_image_to_s3(bucket_name, key, image_path):
    try:
        s3 = boto3.client('s3')
        with image_path.open('rb') as img:
            s3.put_object(Bucket=bucket_name, Key=key, Body=img)
    except FileNotFoundError as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. A FileNotFoundError has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. A FileNotFoundError has occurred.\n{str(e)}", 500
    except PermissionError as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. A PermissionError has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. A PermissionError has occurred.\n{str(e)}", 500
    except IsADirectoryError as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. An IsADirectoryError has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. An IsADirectoryError has occurred.\n{str(e)}", 500
    except OSError as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. An {type(e).__name__} has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. An {type(e).__name__} has occurred.\n{str(e)}", 500
    except boto_exceptions.ProfileNotFound as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. A ProfileNotFound has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. A ProfileNotFound has occurred.\n{str(e)}", 500
    except boto_exceptions.ClientError as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. A ClientError has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. A ClientError has occurred.\n{str(e)}", 500
    except boto_exceptions.EndpointConnectionError as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. An EndpointConnectionError has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. An EndpointConnectionError has occurred.\n{str(e)}", 500
    except boto_exceptions.NoCredentialsError as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. A NoCredentialsError has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. A NoCredentialsError has occurred.\n{str(e)}", 500
    except boto_exceptions.ParamValidationError as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. A ParamValidationError has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. A ParamValidationError has occurred.\n{str(e)}", 500
    except Exception as e:
        logger.exception(f"Upload to {bucket_name}/{key} failed. An Unknown {type(e).__name__} has occurred.\n{str(e)}")
        return f"Upload to {bucket_name}/{key} failed. An Unknown {type(e).__name__} has occurred.\n{str(e)}", 500

    logger.info(f"Upload to {bucket_name}/{key} succeeded.")
    return f"Upload to {bucket_name}/{key} succeeded.", 200

def download_image_from_s3(bucket_name, key, image_path):
    if not os.path.exists(images_prefix):
        os.makedirs(images_prefix)

    try:
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket_name, Key=key)
    except boto_exceptions.ProfileNotFound as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. A ProfileNotFound has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. A ProfileNotFound has occurred.\n{str(e)}", 500
    except boto_exceptions.ClientError as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. A ClientError has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. A ClientError has occurred.\n{str(e)}", 500
    except boto_exceptions.EndpointConnectionError as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. An EndpointConnectionError has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. An EndpointConnectionError has occurred.\n{str(e)}", 500
    except boto_exceptions.NoCredentialsError as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. A NoCredentialsError has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. A NoCredentialsError has occurred.\n{str(e)}", 500
    except Exception as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. An Unknown {type(e).__name__} has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. An Unknown {type(e).__name__} has occurred.\n{str(e)}", 500

    try:
        with open(image_path, 'wb') as img:
            img.write(response['Body'].read())
    except PermissionError as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. A PermissionError has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. A PermissionError has occurred.\n{str(e)}", 500
    except IsADirectoryError as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. An IsADirectoryError has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. An IsADirectoryError has occurred.\n{str(e)}", 500
    except OSError as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. An {type(e).__name__} has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. An {type(e).__name__} has occurred.\n{str(e)}", 500
    except Exception as e:
        logger.exception(f"Download from {bucket_name}/{key} failed. An Unknown {type(e).__name__} has occurred.\n{str(e)}")
        return f"Download from {bucket_name}/{key} failed. An Unknown {type(e).__name__} has occurred.\n{str(e)}", 500

    logger.info(f"Download from {bucket_name}/{key} to {image_path} succeeded.")
    return f"Download from {bucket_name}/{key} to {image_path} succeeded.", 200

def identify(img_name, prediction_id):
    logger.info(f'Prediction: {prediction_id}. Start processing')

    if not img_name:
        logger.exception(f'Prediction: {prediction_id}/{img_name}. No image parameter was passed or is empty.')
        return f'Prediction: {prediction_id}/{img_name}. No image parameter was passed or is empty.', 500

    # The bucket name and prefix are provided as env variables BUCKET_NAME and BUCKET_PREFIX respectively.
    original_img_path = images_prefix + "/" + img_name

    # Download img_name from S3 and store it to a local path from the original_img_path variable.
    response = download_image_from_s3(images_bucket, original_img_path, original_img_path)

    if response[1] != 200:
        logger.exception(f'Prediction: {prediction_id}/{img_name} failed.')
        return f'Prediction: {prediction_id}/{img_name} failed.\n\n{response[0]}', response[1]

    # Predicts the objects in the image
    run(
        weights='yolov5s.pt',
        data='data/coco128.yaml',
        source=original_img_path,
        project='static/data',
        name=prediction_id,
        save_txt=True
    )

    logger.info(f'Prediction: {prediction_id}/{img_name}. Done')

    # This is the path for the predicted image with labels
    # The predicted image typically includes bounding boxes drawn around the detected objects, along with class labels and possibly confidence scores.
    predicted_img_path = Path(f'static/data/{prediction_id}/{img_name}')

    # Uploads the predicted image (predicted_img_path) to S3.
    response = upload_image_to_s3(images_bucket, original_img_path, predicted_img_path)

    if response[1] != 200:
        logger.exception(f'Prediction: {prediction_id}/{img_name} failed.')
        return f'Prediction: {prediction_id}/{img_name} failed.\n\n{response[0]}', response[1]

    # Parse prediction labels and create a summary
    pred_summary_path = Path(f'static/data/{prediction_id}/labels/{img_name.split(".")[0]}.txt')
    if not pred_summary_path.exists():
        logger.exception(f'Prediction: {prediction_id}/{img_name}. Prediction result not found')
        return f'Prediction: {prediction_id}/{img_name}. Prediction result not found', 404

    with pred_summary_path.open(mode='r', encoding='utf-8') as f:
        labels = f.read().splitlines()
        labels = [line.split(' ') for line in labels]
        labels = [{
            'class': names[int(l[0])],
            'cx': float(l[1]),
            'cy': float(l[2]),
            'width': float(l[3]),
            'height': float(l[4]),
        } for l in labels]

    prediction_summary = {
        'prediction_id': prediction_id,
        'original_img_path': original_img_path,
        'predicted_img_path': predicted_img_path.as_posix(),
        'labels': labels,
        'time': time.time()
    }

    logger.info(f'Prediction: {prediction_id}/{img_name} was executed successfully.\n\nPrediction summary:\n{prediction_summary}')
    return prediction_summary, 200

def write_to_db(prediction_id, prediction_summary):
    # MongoDB credentials
    username = 'admin'
    try:
        raw_password = get_docker_secret('mongo_db_password')
        if raw_password is None:
            raise ValueError("DB Password is not available")
    except ValueError as e:
        logger.exception(f"An error has occurred.\n{str(e)}")
        return f"An error has occurred.\n{str(e)}", 500

    auth_db = 'admin'

    # URL encode the password
    encoded_password = quote_plus(raw_password)

    # MongoDB URI including authentication details
    uri = f"mongodb://{username}:{encoded_password}@mongo1:27017/{auth_db}"

    retry = 0
    max_retries = 3
    curr_exception = None
    while retry < max_retries:
        # Store the prediction_summary in MongoDB
        try:
            # Connect to the MongoDB server (assumes MongoDB is running on the default port on localhost)
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            # Force a connection to test server availability
            client.admin.command('ping')

            # Select the database
            db = client['image_predictions']

            # Select the collection
            collection = db['prediction_results']

            # Insert a document
            collection.insert_one(prediction_summary)

            break
        except mongo_errors.ServerSelectionTimeoutError as e:
            logger.exception(f"Server selection timed out. Could not connect to MongoDB.\n{str(e)}")
            curr_exception = f"Server selection timed out. Could not connect to MongoDB.\n{str(e)}"
        except mongo_errors.WriteError as e:
            logger.exception(f"Write operation failure.\n{str(e)}")
            curr_exception = f"Write operation failure.\n{str(e)}"
        except mongo_errors.OperationFailure as e:
            logger.exception(f"Operation failed.\n{str(e)}")
            curr_exception = f"Operation failed.\n{str(e)}"
        except mongo_errors.ConnectionFailure as e:
            logger.exception(f"Failed to connect to MongoDB.\n{str(e)}")
            curr_exception = f"Failed to connect to MongoDB.\n{str(e)}"
        except TypeError as e:
            logger.exception(f"Write operation failure.\n{str(e)}")
            curr_exception = f"Write operation failure.\n{str(e)}"
            retry = 3
            break
        except Exception as e:
            logger.exception(f"An Unknown {type(e).__name__} has occurred.\n{str(e)}")
            curr_exception = f"An Unknown {type(e).__name__} has occurred.\n{str(e)}"
            retry = 3
            break

        retry += 1
        if retry < max_retries:
            time.sleep(3)

    if retry == max_retries:
        return curr_exception, 500

    logger.info("Image prediction details were written to the DB successfully")

    converted_data = convert_objectid(prediction_summary)
    return converted_data, 200