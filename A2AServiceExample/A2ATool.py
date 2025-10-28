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

def download_pdf(url, year):
    response =  requests.get(url)
    local_file_name = year+'.pdf'
    if response.status_code == 200:
        with open(local_file_name, 'wb') as file:
            file.write(response.content)
        print(f"PDF downloaded successfully: {local_file_name}")
        return local_file_name
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
def ingest_files_and_create_knowledge_base(animal:str, state:str, file_details: dict[str, str]) :
    """
    Downloads PDF files from provided URLs, stores them in an S3 bucket, and creates or updates a vector-based Amazon Bedrock knowledge base.

    This tool performs the following steps:
    1. Generates a unique name for each file.
    2. Uploads the files to an S3 bucket (creates the bucket if it doesn't exist).
    3. Creates or updates a Bedrock knowledge base using the uploaded files.

    Parameters:
        animal (str): The type of animal the data is related to (e.g., "deer").
        state (str): The U.S. state the data is associated with (e.g., "Illinois").
        file_details (dict[str, str]): A dictionary of years and urls:
            - key (str): The key should be the year the data in the file represents.
            - value (str): The value should be the direct link to a downloadable PDF file.

    Returns:
        str: The ID of the created or updated knowledge base.

    Example:
        ingest_files_and_create_knowledge_base(
            animal="deer",
            state="Illinois",
            file_details=[
                {"2022", "https://example.com/deer-report-2022.pdf"},
                {"2023", "https://example.com/deer-report-2023.pdf"}
            ]
        )

    """ 
    ## Fill loop here 
    files = []
    for file in file_details.items():
        year, url = file
        source = download_pdf(url, year)
        target = f"{animal.lower()}/{state.lower()}/{year}.pdf"
        files.append((source,target))
    kb_id = create_knowledge_base(files)
    ## at the end of this function we need to write the kb_id to an environment variable so that it can be referenced later in the jupyter notebook
    os.environ["BEDROCK_KB_ID"] = kb_id
    return kb_id


# system_prompt = """
# You are Hunting data scraping agent, your job is to fetch hunting data from a given web page and create knowledge bases from the PDFs on the web page.
# [Instructions]
# - you will be provided a URL to a states hunting website and an animal
# - Use HTTP GET to load the web page for the url provided
# - Identify the state that the webpage is for
# - Identify all the pdf files from the page for the animal that is provided. Pdf files should have a particular year in which they contain data for
# - If a year is presented as a range (e.g. 2022-2023) then that you should treat the year as the beginning of the range
# - If there are multiple pdf files for a single year and animal then choose one pdf for that year
# - If there are multiple pdf files for a single year and animal pick the file that is for the general season if possible
# - If there are multiple pdf files for a single year and animal but you are unable to identify a general season file then pick the first file file that animal and year
# - Using the tool you have been provided
#     - Ingest all the files that you identified and generate knowledge base name with the provided animal name and the state that you identified
#     - If this tool fails stop and tell the user there is a problem
# """

system_prompt = """
  You are a test Agent you will get a request from another agent, answer their request
"""

web_scraping_agent = Agent(
    tools=[ingest_files_and_create_knowledge_base, http_request ],
    system_prompt = system_prompt,
    model=model,
    description="A test agent that responds to requests from other agents."
    # description="An agent that scrapes hunting data from state websites and creates knowledge bases from the PDFs found on those pages."
)

a2a_server = A2AServer(
    agent=web_scraping_agent,
    http_url="http://host.docker.internal:9000"
)

# Create FastAPI app from A2A server
fastapi = a2a_server.to_fastapi_app()

# Add health check endpoint
@fastapi.get("/health")
def health_check():
    return {"status": "healthy", "service": "strands-a2a-service"}

if __name__ == "__main__":
    # Bind to 0.0.0.0 to accept connections from outside the container
    print("Starting A2A server on 0.0.0.0:9000...")
    uvicorn.run(fastapi, host="0.0.0.0", port=9000)