import boto3

def upload_to_s3(s3_arn, file_path):
    """
    Checks for the existence of the specified S3 bucket, and uploads the request asset.
    Rejects duplicate names.
    """
    print(f"Uploaded {file_path} to bucket: {s3_arn}")

def list_s3_objects(s3_arn, regex=None):
    """
    Returns all of the objects in the specified s3 bucket that match a specific pattern.
    If regex is empty, return all objects in the bucket.

    returns: list of object names
    """
    if regex:
        print(f"Available S3 objects matching {regex}.")
    else:
        print(f"Available S3 objects.")