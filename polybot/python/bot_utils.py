import boto3
from botocore import exceptions as boto_exceptions
from loguru import logger
import json
from collections import Counter

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

def parse_result(json_data):
    # Parse the JSON data
    data = json.loads(json_data)

    # Extract the labels
    labels = data["labels"]

    # Create a list of class values from the labels
    class_names = [label["class"] for label in labels if "class" in label]

    # Count the occurrences of each class
    class_counts = Counter(class_names)

    # Create a single text result
    return_text = "Detected Objects:\n"
    for class_name, count in class_counts.items():
        return_text += f"{class_name.capitalize()}: {count}\n"

    return return_text