import boto3
from botocore import exceptions as boto_exceptions
from loguru import logger
from collections import Counter
import os

aws_profile = os.getenv("AWS_PROFILE", None)
if aws_profile is not None and aws_profile == "dev":
    boto3.setup_default_session(profile_name=aws_profile)

def upload_image_to_s3(bucket_name, key, image_path):
    s3 = boto3.client('s3')
    try:
        with open(image_path, 'rb') as img:
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

def download_image_from_s3(bucket_name, key, image_path, images_prefix):
    s3 = boto3.client('s3')

    if not os.path.exists(images_prefix):
        os.makedirs(images_prefix)

    try:
        response = s3.get_object(Bucket=bucket_name, Key=key)
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

def parse_result(json_data) -> str:
    # Extract the labels
    labels = json_data["labels"]

    # Create a list of class values from the labels
    class_names = [label["class"] for label in labels if "class" in label]

    # Count the occurrences of each class
    class_counts = Counter(class_names)

    # Create a single text result
    return_text = "Detected Objects:\n"
    for class_name, count in class_counts.items():
        return_text += f"{class_name.capitalize()}: {count}\n"

    return return_text