import argparse
import os
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from intellidoc.aws import upload_to_s3, list_s3_objects

SUPPORTED_FILE_TYPES = {".json", ".pdf", ".csv"}

load_dotenv()
S3_ARN = os.getenv("S3_ARN")
API_KEY = os.getenv("GEMINI_API_KEY")

def cmd_query(args):
    """Run a query against the data sources defined in the config file."""
    client = OpenAI(api_key=API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")

    query = input("Enter your query: \n")
    print(query)


def cmd_list_sources(args):
    """List the objects in the S3 bucket, according to a pattern."""
    objects = list_s3_objects(S3_ARN, args.regex)

    if objects:
        print("List of Sources: \n")
        for obj in objects:
            print(obj)
    else:
        print("S3 is empty.")


def cmd_add_sources(args):
    """Add a new data source to AWS. Just performs an upload to AWS, after performing checks to
    ensure compatible file type."""

    source_files = []
    for source in args.sources:
        source_path = Path(source)

        if not source_path.exists():
            print(f"Source does not exist: {source}")
            return 1

        if source_path.is_file():
            if source_path.suffix.lower() not in SUPPORTED_FILE_TYPES:
                print(f"Unsupported file type: {source_path}")
                return 1
            source_files.append(source_path)
        elif source_path.is_dir():
            source_files.extend(
                path for path in source_path.rglob("*")
                if path.is_file() and path.suffix.lower() in SUPPORTED_FILE_TYPES
            )

    if not source_files:
        print("No supported JSON, PDF, or CSV files found.")
        return 1

    for source_file in source_files:
        upload_arn = upload_to_s3(S3_ARN, str(source_file))
        print(f"Confirmed upload: {source_file} to AWS: {upload_arn}")

    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="intellidoc", description="Ask queries about Delight using Amazon Redshift data warehouse.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    query_parser = subparsers.add_parser("query", help="Run a query against the data sources")
    query_parser.set_defaults(func=cmd_query)

    list_parser = subparsers.add_parser("list-sources", help="List configured data sources")
    list_parser.add_argument("--regex", required=False, type=str)
    list_parser.set_defaults(func=cmd_list_sources)

    add_source_parser = subparsers.add_parser("add-sources", help="Add a data sources to the RAG data warehouse.")
    add_source_parser.add_argument("sources", nargs="+", help="Files or directories containing JSON, PDF, or CSV sources.")
    add_source_parser.set_defaults(func=cmd_add_sources)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    exit_code = args.func(args)
    raise SystemExit(exit_code)