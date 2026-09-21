import os
import time
import hashlib, base64

import boto3
from dotenv import load_dotenv

load_dotenv()


def _connect_to_rds():
    import psycopg2

    return psycopg2.connect(
        host=os.environ["RDS_HOST"],
        port=os.getenv("RDS_PORT", "5432"),
        dbname=os.environ["RDS_DATABASE"],
        user=os.environ["RDS_USER"],
        password=os.environ["RDS_PASSWORD"],
        connect_timeout=int(os.getenv("RDS_CONNECT_TIMEOUT", "10")),
    )


def wait_for_document(object_key, timeout_seconds=None, poll_seconds=None):
    """Wait for the Lambda-created RDS row and return its id and text."""
    timeout_seconds = timeout_seconds or int(os.getenv("RDS_POLL_TIMEOUT_SECONDS", "900"))
    poll_seconds = poll_seconds or int(os.getenv("RDS_POLL_SECONDS", "5"))
    table = os.getenv("RDS_DOCUMENT_TABLE", "documents")
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        with _connect_to_rds() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"SELECT id, text FROM {table} WHERE object_key = %s ORDER BY id DESC LIMIT 1",
                    (object_key,),
                )
                row = cursor.fetchone()
        if row:
            return {"id": row[0], "text": row[1]}
        time.sleep(poll_seconds)

    raise TimeoutError(f"Timed out waiting for RDS document: {object_key}")


def process_document(object_key):
    """Poll RDS, chunk and embed a PDF, then write vectors to Redshift and OpenSearch."""
    document = wait_for_document(object_key)
    chunks = _chunk_text(document["text"])
    embeddings = _embed_chunks(chunks)
    _write_to_redshift(document["id"], object_key, chunks, embeddings)
    return document["id"]


def _chunk_text(text):
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "150")),
    )
    return splitter.split_text(text)


def _embed_chunks(chunks):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    return model.encode(chunks, normalize_embeddings=True).tolist()


def _write_to_redshift(document_id, object_key, chunks, embeddings):
    import psycopg2

    with psycopg2.connect(
        host=os.environ["REDSHIFT_HOST"],
        port=os.getenv("REDSHIFT_PORT", "5439"),
        dbname=os.environ["REDSHIFT_DATABASE"],
        user=os.environ["REDSHIFT_USER"],
        password=os.environ["REDSHIFT_PASSWORD"],
    ) as connection:
        with connection.cursor() as cursor:
            table = os.getenv("REDSHIFT_EMBEDDING_TABLE", "document_embeddings")
            for position, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                cursor.execute(
                    f"""
                    INSERT INTO {table} (document_id, object_key, chunk_index, text, embedding)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (document_id, object_key, position, chunk, embedding),
                )
        connection.commit()

def verify_lambda_function(lambda_arn):
    lambda_client = boto3.client("lambda")
    with open("function.zip", "rb") as f:
        local_hash = base64.b64encode(hashlib.sha256(f.read()).digest()).decode()

    remote_hash = lambda_client.get_function(FunctionName="pdf-processor")["Configuration"]["CodeSha256"]

    assert local_hash == remote_hash, "Deployed code doesn't match local file!"