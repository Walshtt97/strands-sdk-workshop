# Strands SDK Workshop

A hands-on workshop for learning AWS Strands SDK for building AI Agents.

## Prerequisites

- AWS Account with Bedrock access
- AWS CLI configured or AWS credentials
- Docker and Docker Compose (for containerized setup)

## Running with Docker (Recommended)

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd strands-sdk-workshop
   ```

2. **Configure AWS credentials (choose ONE option):**
   
   **Option A: Using Local AWS CLI (Recommended)**
   ```bash
   # First, configure AWS CLI if you haven't already
   aws configure
   
   # Then uncomment the AWS credentials volume mount in docker-compose.yml
   # Edit docker-compose.yml and uncomment this line:
   # - ~/.aws:/home/workshop/.aws:ro
   ```
   
   **Option B: Using Environment Variables**
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env file with your AWS credentials
   nano .env
   # Uncomment and fill in AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, etc.
   ```

3. **Build and run the container:**
   ```bash
   docker-compose up --build
   ```

4. **Access Jupyter Lab:**
   - Open your browser and go to: http://localhost:8888
   - The Jupyter Lab interface will be available with all workshop materials

### Container Features

- **Ubuntu 22.04** base image with Python 3.10+
- **Jupyter Lab** pre-installed and configured
- **All workshop dependencies** installed from requirements.txt
- **AWS credentials** mounted from your local system
- **Live editing** - changes to notebooks are persisted locally
- **Port 8888** exposed for Jupyter access

### Stopping the Workshop

```bash
# Stop the containers
docker-compose down

# Stop and remove all data (caution: this will delete any work not saved locally)
docker-compose down -v
```

## Manual Setup (Alternative)

If you prefer to run without Docker:

1. **Install Python 3.8+**
2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Start Jupyter:**
   ```bash
   jupyter lab
   ```

## Workshop Content

- **strands-agent-workshop/** - Main workshop notebooks and exercises
- **strands-demo/** - Demo notebooks and examples
- **images/** - Architectural diagrams and visual aids

## Troubleshooting

### Docker Issues

- **Port already in use:** Change the port mapping in docker-compose.yml (e.g., "8889:8888")
- **AWS credentials not working:** Ensure your AWS credentials are properly configured
- **Permission issues:** Make sure Docker has proper permissions on your system

### AWS Issues

- **AWS credentials not found:** 
  - If using Option A: Make sure you uncommented the volume mount in docker-compose.yml
  - If using Option B: Make sure you created a .env file with your credentials
  - Test with: `docker exec -it strands-sdk-workshop aws sts get-caller-identity`
- **Bedrock access denied:** Ensure your AWS account has Bedrock access enabled
- **Region issues:** Make sure you're using a region where Bedrock is available (default: us-east-1)
- **Permission denied on ~/.aws:** Try `chmod 644 ~/.aws/credentials ~/.aws/config`

## Support

For issues and questions related to the workshop content, please refer to the individual notebook instructions or create an issue in this repository.