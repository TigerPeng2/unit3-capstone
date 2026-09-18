# Intellidoc: Intelligent Document Search Pipeline
This project is an AWS-based document processing pipeline accompanied by a CLI RAG query interface, named Intellidoc

The document processing pipeline automates document ingestion, ETL, vectorization, structured data storage, and support for Retrieval-Augmented Generation (RAG) queries.

The tool accepts PDFs, CSVs, and JSONs as inputs.

## Installing and Configuring the Tool
Run 

`python -m venv .venv`

`source .venv/bin/activate`

`pip install .` to install the pyproject.toml specified dependencies

`pip install -e .` to install the package as a module

Then configure your AWS credentials using

`aws configure`

Ensure that your IAM identity has the proper permissions to generate and configure all the necessary resources for this project: S3 Buckets, Lambda Functions, Textract Instances, OpenSearch services, Redshift Warehouses, RDS Databases.

The information that you are required to put in the .env:
- GEMINI_API_KEY - to allow for data generation as well as orchestration calls for the query interface

## Generating Data
To generate the artificial data that will be inserted into the system, run:

`python generate-data.py`

## Running the CLI
In order to run the tool, run the project as a module

`python -m intellidoc add-source`
To add a source to the data ingestion pipeline.

`python -m intellidoc query`
To run a query using the CLI RAG tool.

## Using the Tool

## Architecture
The project has a handful of main components
- Data Generation
- Data Ingestion
- Data Warehouse
- Query Interface

### Data Generation
This artifical data generation code is mostly taken from the previous capstone where the example queries were in a similar domain.

It has been modified to output text files in a PDF form rather that a .txt form, to generate .csvs instead of inputting to a .sqlite3, generate a JSON format customer support tickets document, and output a data governance policy document that implies the required columns mentioned in the capstone specification.

Generate the data using

`python generate_data.py`

### Data Ingestion
The data ingestion pipeline allows for both unstructed (PDF) and structured (CSV, JSON) data.

The ingestion process varies by data type.

#### PDF

Data Selection (CLI) -> PDF -> Text (Textract) -> Extracted Text

1. Extracted Text -> Text Chunking -> Embedding (Sentence Transformers) -> Embedding Indexing (OpenSearch) -> Load to Redshift
2. Extracted Text -> RDS Table (storage with metadata)

#### CSV / JSON
Data Selection (CLI) -> Discover Metadata (Glue Crawler) -> ETL (Glue Transform) -> Load to Redshift

### Data Warehouse
Redshift serves as the data warehouse for this project, storing the the structured data (CSV/JSON), as well as the embedded chunks extracted from PDFs.

At query time, the agent is capable both of submitting SQL queries against ingested tables, as well as using Redshift's native similarity search to find relevant chunks, using the attached metadata to bring the relevant document into context.

### Query Interface
This query interface is largely borrowed from the Unit 2 Capstone, with subcommands for adding data sources, listing data sources, and inputting a query.

The query is input into an orchestrator, which has access to metadata regarding the names and structures of data sources.  
The orchestrator first determines which resources must be recruited, then queries for the schemas of those data sources.  
Then the query agent creates a structured request to redshift and a followup request for the full-text to RDS if needed, before outputting a response (text and/or graphic).

## Notes
- I had no idea what "Populate Redshift with both structured data and vector embeddings" meant, so I just duplicated the OpenSearch stored embeddings into Redshift.

## TODO
- Configure S3 bucket
- Figure out how to do text chunking