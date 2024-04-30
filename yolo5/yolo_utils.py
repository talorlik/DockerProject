import boto3
from botocore import exceptions as boto_exceptions
from loguru import logger
from pymongo import MongoClient
from pymongo import errors as mongo_errors
import os
from urllib.parse import quote_plus
from get_docker_secret import get_docker_secret

def upload_image_to_s3(bucket_name, key, image_path):
    s3 = boto3.client('s3')
    try:
        with open(image_path, 'rb') as img:
            s3.put_object(Bucket=bucket_name, Key=key, Body=img)
    except FileNotFoundError as e:
        logger.exception(f"A FileNotFoundError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A FileNotFoundError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except PermissionError as e:
        logger.exception(f"A PermissionError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A PermissionError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except FileExistsError as e:
        logger.exception(f"A FileExistsError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A FileExistsError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except IsADirectoryError as e:
        logger.exception(f"An IsADirectoryError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An IsADirectoryError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except OSError as e:
        logger.exception(f"An {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except boto_exceptions.ClientError as e:
        logger.exception(f"A ClientError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A ClientError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except boto_exceptions.EndpointConnectionError as e:
        logger.exception(f"An EndpointConnectionError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An EndpointConnectionError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except boto_exceptions.NoCredentialsError as e:
        logger.exception(f"A NoCredentialsError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A NoCredentialsError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except boto_exceptions.ParamValidationError as e:
        logger.exception(f"A ParamValidationError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A ParamValidationError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except Exception as e:
        logger.exception(f"An Unknown {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An Unknown {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}", 500

    logger.info(f"Image uploaded successfully to S3 bucket: {bucket_name}/{key}")
    return f"Image uploaded successfully to S3 bucket: {bucket_name}/{key}", 200

def download_image_from_s3(bucket_name, key, image_path):
    s3 = boto3.client('s3')
    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
    except boto_exceptions.ClientError as e:
        logger.exception(f"A ClientError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A ClientError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except boto_exceptions.EndpointConnectionError as e:
        logger.exception(f"An EndpointConnectionError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An EndpointConnectionError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except boto_exceptions.NoCredentialsError as e:
        logger.exception(f"A NoCredentialsError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A NoCredentialsError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except Exception as e:
        logger.exception(f"An Unknown {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An Unknown {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}", 500

    try:
        with open(image_path, 'wb') as img:
            img.write(response['Body'].read())
    except FileNotFoundError as e:
        logger.exception(f"A FileNotFoundError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A FileNotFoundError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except PermissionError as e:
        logger.exception(f"A PermissionError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A PermissionError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except FileExistsError as e:
        logger.exception(f"A FileExistsError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"A FileExistsError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except IsADirectoryError as e:
        logger.exception(f"An IsADirectoryError has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An IsADirectoryError has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except OSError as e:
        logger.exception(f"An {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}", 500
    except Exception as e:
        logger.exception(f"An Unknown {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}")
        return f"An Unknown {type(e).__name__} has occurred {bucket_name}/{key}.\n{str(e)}", 500

    logger.info(f"Image downloaded successfully from S3 bucket: {bucket_name}/{key} to {image_path}")
    return f"Image downloaded successfully from S3 bucket: {bucket_name}/{key} to {image_path}", 200

def write_to_db(prediction_summary):
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
    except mongo_errors.ServerSelectionTimeoutError as e:
        logger.exception(f"Server selection timed out. Could not connect to MongoDB.\n{str(e)}")
        return f"Server selection timed out. Could not connect to MongoDB.\n{str(e)}", 500
    except mongo_errors.OperationFailure as e:
        logger.exception(f"Operation failed.\n{str(e)}")
        return f"Operation failed.\n{str(e)}", 500
    except mongo_errors.ConnectionFailure as e:
        logger.exception(f"Failed to connect to MongoDB.\n{str(e)}")
        return f"Failed to connect to MongoDB.\n{str(e)}", 500
    except Exception as e:
        logger.exception(f"An Unknown {type(e).__name__} has occurred.\n{str(e)}")
        return f"An Unknown {type(e).__name__} has occurred.\n{str(e)}", 500

    logger.info("Image prediction details were written to the DB successfully")
    return "Image prediction details were written to the DB successfully", 200