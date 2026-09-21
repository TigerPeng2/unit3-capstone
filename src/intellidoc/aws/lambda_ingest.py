import json
import logging
import os
import time
from urllib.parse import unquote_plus

import boto3
import psycopg2
from dotenv import load_dotenv


load_dotenv()
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)


def _connect_to_rds():
	return psycopg2.connect(
		host=os.environ["RDS_HOST"],
		port=os.getenv("RDS_PORT", "5432"),
		dbname=os.environ["RDS_DATABASE"],
		user=os.environ["RDS_USER"],
		password=os.environ["RDS_PASSWORD"],
		connect_timeout=int(os.getenv("RDS_CONNECT_TIMEOUT", "10")),
	)


def _extract_pdf_text(bucket_name, object_key):
	textract = boto3.client("textract")
	response = textract.start_document_text_detection(
		DocumentLocation={"S3Object": {"Bucket": bucket_name, "Name": object_key}}
	)
	job_id = response["JobId"]
	deadline = time.monotonic() + int(os.getenv("TEXTRACT_TIMEOUT_SECONDS", "840"))

	while time.monotonic() < deadline:
		result = textract.get_document_text_detection(JobId=job_id)
		status = result["JobStatus"]
		if status == "SUCCEEDED":
			blocks = result.get("Blocks", [])
			next_token = result.get("NextToken")
			while next_token:
				result = textract.get_document_text_detection(JobId=job_id, NextToken=next_token)
				blocks.extend(result.get("Blocks", []))
				next_token = result.get("NextToken")
			return "\n".join(block["Text"] for block in blocks if block["BlockType"] == "LINE")
		if status == "FAILED":
			raise RuntimeError(f"Textract failed for s3://{bucket_name}/{object_key}")
		time.sleep(int(os.getenv("TEXTRACT_POLL_SECONDS", "5")))

	raise TimeoutError(f"Textract timed out for s3://{bucket_name}/{object_key}")


def _store_document(bucket_name, object_key, text):
	table = os.getenv("RDS_DOCUMENT_TABLE", "documents")
	with _connect_to_rds() as connection:
		with connection.cursor() as cursor:
			cursor.execute(
				f"""
				INSERT INTO {table} (object_key, source_uri, text)
				VALUES (%s, %s, %s)
				ON CONFLICT (object_key) DO UPDATE
				SET text = EXCLUDED.text, source_uri = EXCLUDED.source_uri
				RETURNING id
				""",
				(object_key, f"s3://{bucket_name}/{object_key}", text),
			)
			document_id = cursor.fetchone()[0]
		connection.commit()
	return document_id


def lambda_handler(event, context):
	"""Extract PDF text from S3 events and store it in RDS."""
	results = []
	for record in event.get("Records", []):
		bucket_name = record["s3"]["bucket"]["name"]
		object_key = unquote_plus(record["s3"]["object"]["key"])
		if not object_key.lower().endswith(".pdf"):
			LOGGER.info("Skipping non-PDF object: s3://%s/%s", bucket_name, object_key)
			continue

		text = _extract_pdf_text(bucket_name, object_key)
		document_id = _store_document(bucket_name, object_key, text)
		results.append({"id": document_id, "object_key": object_key})
		LOGGER.info("Stored document %s in RDS", document_id)

	return {"statusCode": 200, "body": json.dumps(results)}
