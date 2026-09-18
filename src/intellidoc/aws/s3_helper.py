import os
import re
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


load_dotenv()


def _get_bucket_name(s3_arn=None):
    s3_arn = s3_arn or os.getenv("S3_ARN")
    if not s3_arn:
        raise ValueError("S3_ARN is not configured.")

    arn_parts = s3_arn.split(":")
    if len(arn_parts) != 6 or arn_parts[0] != "arn" or arn_parts[2] != "s3" or not arn_parts[5]:
        raise ValueError("S3_ARN must be an S3 bucket ARN, such as arn:aws:s3:::bucket-name.")

    return arn_parts[5].split("/", 1)[0]


def upload_to_s3(s3_arn, file_path):
    """
    Upload a local file to the S3 bucket identified by s3_arn or S3_ARN.

    Raises FileExistsError when the object key already exists.
    """
    bucket_name = _get_bucket_name(s3_arn)
    file_path = Path(file_path)
    if not file_path.is_file():
        raise FileNotFoundError(f"Source file does not exist: {file_path}")

    object_key = file_path.name
    s3_client = boto3.client("s3")
    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
    except ClientError as error:
        status_code = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code != 404:
            raise
    else:
        raise FileExistsError(f"S3 object already exists: s3://{bucket_name}/{object_key}")

    s3_client.upload_file(str(file_path), bucket_name, object_key)
    return f"s3://{bucket_name}/{object_key}"


def list_s3_objects(s3_arn=None, regex=None):
    """
    Return object keys in the S3 bucket matching regex, if provided.

    The bucket is read from s3_arn or the S3_ARN environment variable.
    """
    bucket_name = _get_bucket_name(s3_arn)
    pattern = re.compile(regex) if regex else None
    s3_client = boto3.client("s3")
    object_keys = []

    paginator = s3_client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket_name):
        for item in page.get("Contents", []):
            key = item["Key"]
            if pattern is None or pattern.search(key):
                object_keys.append(key)

    return object_keys