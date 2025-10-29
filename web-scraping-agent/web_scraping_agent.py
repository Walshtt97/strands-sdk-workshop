from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from strands_tools import http_request
import os
import requests
import sys
sys.path.append('./utils')
from knowledge_base_management import create_knowledge_base_with_s3_vectors, retrieve_knowledge_base, update_knowledge_base_with_s3_vectors
import uvicorn

# Configuration variables
model = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-20250514-v1:0")
user = os.getenv("USER_NAME", "workshop")
region = os.getenv("AWS_REGION", "us-east-1")

os.environ["BYPASS_TOOL_CONSENT"] = "true"

@tool
def download_pdf(file_details: dict[str, str]):
    """
    Downloads files from provided file details.

    Parameters:
        file_details (dict[str, str]): A dictionary of names and urls:
            - key (str): The key should be the name of the file.
            - value (str): The value should be the direct link to a downloadable.

    Returns:
        list: A list of downloaded files.
    """
    downloaded_files = []
    for name, url in file_details.items():
        response = requests.get(url)
        if response.status_code == 200:
            with open(name, 'wb') as file:
                file.write(response.content)
            print(f"PDF downloaded successfully: {name}")
        else:
            print(f"Failed to download PDF. Status code: {response.status_code}")

def create_knowledge_base(files, topic= f"unverified-{user}"):
    ## Fill this in Referncing functions in knowledge_base_management.py
    kb_id =  retrieve_knowledge_base(topic)
    if kb_id is None:
        return create_knowledge_base_with_s3_vectors(topic, files, region)
    else:
        return update_knowledge_base_with_s3_vectors(topic, files, kb_id, region)

@tool
def ingest_files_and_create_knowledge_base(file_details: list[str]) :
    """
    Downloads PDF files from provided URLs, stores them in an S3 bucket, and creates or updates a vector-based Amazon Bedrock knowledge base.

    This tool performs the following steps:
    1. Uploads the files to an S3 bucket (creates the bucket if it doesn't exist).
    2. Creates or updates a Bedrock knowledge base using the uploaded files.

    Parameters:
        file_details (List[str]): A list of file names to download and process.

    Returns:
        str: The ID of the created or updated knowledge base.

    Example:
        update_knowledge_base(
            file_details=[
                {"deer_statistics_illinois_2022", "https://example.com/deer-report-2022.pdf"},
                {"deer_statistics_illinois_2023", "https://example.com/deer-report-2023.pdf"}
            ]
        )

    """ 
    ## Fill loop here 
    kb_id = create_knowledge_base(files)
    ## at the end of this function we need to write the kb_id to an environment variable so that it can be referenced later in the jupyter notebook
    return kb_id


system_prompt = """
You are web scraping agent specialized in hunting data, your job is to fetch hunting data from a given web page and maintain knowledge bases from data found on those websites.
[Instructions]
1. you will be provided at least one URL to scrape
2. Use HTTP GET to load the web page for the url provided
3. Analyze the content of the web page
    - Identify what state the webpage is for
    - Identify an animal(s) that the webpage is has data on
    - Identify if the web page links to any files on the page
4. Generate a text file that summarizes what you found on the page
5. Download all the files that you found with the tool provided
6. Update the knowledge base with the tool provided
    - Ingest the summary you created and the downloaded files and create/update a knowledge base name with those files
    - If this tool fails stop and tell the user there is a problem
"""

web_scraping_agent = Agent(
    tools=[ingest_files_and_create_knowledge_base, download_pdf, http_request],
    system_prompt = system_prompt,
    model=model,
    description="An agent that scrapes hunting data from websites and maintains knowledge bases from data found on those websites."
)

a2a_server = A2AServer(
    agent=web_scraping_agent,
    http_url="http://host.docker.internal:9000"
)

# a2a_server.serve()

# Create FastAPI app from A2A server
fastapi = a2a_server.to_fastapi_app()

# Add health check endpoint
@fastapi.get("/health")
def health_check():
    return {"status": "healthy", "service": "web-scraping-agent"}


if __name__ == "__main__":
    # Bind to 0.0.0.0 to accept connections from outside the container
    print("Starting A2A server on 0.0.0.0:9000...")
    uvicorn.run(fastapi, host="0.0.0.0", port=9000)