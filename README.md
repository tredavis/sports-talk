# Sports Talk Application

![Application Architecture](https://img.shields.io/badge/Architecture-RAG_Architecture-blue)

## Table of Contents

- [Overview](#overview)
- [Architecture Diagram](#architecture-diagram)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
  - [Local Setup](#local-setup)
  - [Docker Setup](#docker-setup)
  - [Kubernetes Deployment](#kubernetes-deployment)
- [Crawler Workflow](#crawler-workflow)
- [LLM Integration](#llm-integration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

The **Sports Talk Application** is an advanced solution leveraging Language Learning Models (LLMs) to provide expert-level insights and interactions within the sports domain. Utilizing a Retrieval-Augmented Generation (RAG) architecture, the application seamlessly integrates document retrieval, embedding, and the ChatGPT-3.5 model to deliver accurate and contextually relevant responses.

**Key Components:**

- **Crawler (`SportsDBCrawler`):** Scrapes comprehensive sports player data and stores it in `players.json` for retrieval.
- **Embedding Engine:** Converts textual data into embeddings for efficient similarity searches.
- **Vector Database (ChromaDB):** Stores and manages embeddings to facilitate quick data retrieval.
- **LLM Integration (ChatGPT-3.5):** Enhances responses with sophisticated language understanding and generation capabilities.
- **Backend API (FastAPI):** Serves as the interface between the user and the LLM, handling queries and delivering responses.
- **Containerization (Docker):** Packages the application components for consistent deployment.
- **Orchestration (Kubernetes with Terraform):** Manages deployment, scaling, and maintenance of containerized applications.

## Architecture Diagram

Below is a simplified representation of the application's architecture:

```plaintext
+-----------------+
|  Sports Data    |
|   (players.json)|
+--------+--------+
         |
         | Document Retrieval
         |
+--------v--------+         +-----------------+
|     Crawler     |         |  Embedding      |
| (SportsDBCrawler)|         |  Engine         |
+--------+--------+         +--------+--------+
         |                           |
         | Writes to                  | Generates Embeddings
         |                           |
+--------v--------+          +-------v--------+
|  players.json    | <------> |  ChromaDB      |
| (Data Storage)  |          | (Vector DB)    |
+-----------------+          +-------+--------+
                                     |
                                     | Embedding Retrieval
                                     |
                             +-------v-------+
                             |   Backend API  |
                             |   (FastAPI)    |
                             +-------+-------+
                                     |
                                     | Integrates with
                                     | ChatGPT-3.5
                                     |
                             +-------v-------+
                             |   ChatGPT-3.5  |
                             |     LLM        |
                             +-------+-------+
                                     |
                                     | HTTP Requests
                                     |
                             +-------v-------+
                             |     Users      |
                             +---------------+
```

**Components Detail:**

1. **Sports Data (`players.json`):** Serves as the primary data repository, containing detailed information about sports players.
2. **Crawler (`SportsDBCrawler`):** Extracts player data from various sources and populates `players.json`, ensuring data freshness and accuracy.
3. **Embedding Engine:** Transforms textual data from `players.json` into high-dimensional vectors suitable for similarity searches.
4. **ChromaDB (Vector Database):** Stores embeddings and provides efficient retrieval mechanisms to fetch relevant documents based on user queries.
5. **Backend API (FastAPI):** Acts as the intermediary between users and the LLM, handling query processing, document retrieval, and response generation.
6. **ChatGPT-3.5 (LLM):** Utilizes OpenAI's language model to generate coherent and contextually appropriate responses, augmented by the retrieved documents.
7. **Containerization (Docker):** Ensures that all components run in isolated and reproducible environments.
8. **Orchestration (Kubernetes with Terraform):** Automates deployment, scaling, and management of the application's containerized services.

## Features

- **Expert-Level Responses:** Leveraging ChatGPT-3.5 to provide in-depth and accurate sports-related information.
- **Retrieval-Augmented Generation (RAG):** Combines document retrieval with LLM capabilities for enhanced response quality.
- **Efficient Data Retrieval:** Utilizes embeddings and a vector database to quickly fetch relevant information.
- **Scalable Infrastructure:** Deploys on Kubernetes for resilience and scalability to handle varying loads.
- **Automated Deployment:** Uses Terraform to define and manage infrastructure as code, streamlining setup and maintenance.
- **Extensible Architecture:** Designed to grow into a comprehensive sports expert model, accommodating additional data sources and functionalities.

## Prerequisites

Before setting up the application, ensure you have the following installed:

- **Python 3.10** or higher
- **pip** (Python package manager)
- **Docker** (for containerization)
- **kubectl** (Kubernetes command-line tool)
- **Minikube** or access to a Kubernetes cluster
- **Terraform** (for infrastructure automation)
- **ChromaDB** setup and accessible

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/sports-talk-app.git
cd sports-talk-app
```

### 2. Set Up Python Environment

It's recommended to use a virtual environment to manage dependencies.

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

### 3. Install Dependencies

Ensure you have a `requirements.txt` file in the project root.

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Configuration

Configure necessary environment variables and settings.

1. **ChromaDB Configuration:**

   Ensure that ChromaDB is accessible and configured correctly. Refer to [ChromaDB Documentation](https://www.trychroma.com/docs/) for setup instructions.

2. **LLM API Keys:**

   If using OpenAI's API, set up your API keys as environment variables.

   ```bash
   export OPENAI_API_KEY=your_openai_api_key
   ```

3. **Crawler Settings:**

   Update any crawler-specific settings in `app/scrapers/sportsdb/crawler.py` if necessary, such as `save_frequency` and `backup_frequency`.

## Running the Application

### Local Setup

1. **Run the Crawler:**

   The crawler is responsible for scraping player data and storing it in `players.json`.

   ```bash
   python -m app.scrapers.sportsdb
   ```

   **Note:** Ensure that you have access to the data sources and that your IP isn't rate-limited.

2. **Start the Backend API:**

   Assuming you have a `main.py` for the FastAPI app in the project root.

   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

   Access the API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

### Docker Setup

1. **Build the Docker Image:**

   ```bash
   docker build -t sports-talk-app:latest .
   ```

2. **Run the Docker Container:**

   ```bash
   docker run -d -p 80:80 --name sports-talk-container sports-talk-app:latest
   ```

   The application should now be accessible at `http://localhost`.

### Kubernetes Deployment

Deployment can be managed using Kubernetes manifests or Terraform.

#### Using Kubernetes Manifests

1. **Apply Deployment and Service:**

   ```bash
   kubectl apply -f k8s/deployment.yaml
   ```

2. **Verify Deployment:**

   ```bash
   kubectl get pods -n sports-talk
   kubectl get services -n sports-talk
   ```

#### Using Terraform

1. **Initialize Terraform:**

   ```bash
   cd terraform
   terraform init
   ```

2. **Apply the Configuration:**

   ```bash
   terraform apply
   ```

   Confirm the apply action when prompted.

3. **Verify Deployment:**

   ```bash
   kubectl get pods -n sports-talk
   kubectl get services -n sports-talk
   ```

## Crawler Workflow

The **SportsDBCrawler** is the heart of the data extraction process. Here's a step-by-step explanation of how it functions:

### 1. Initialization

- **Set Up Paths and Directories:**
  - Ensures that the necessary data directories (`app/data` and `app/data/backups`) are created.
- **Load Existing Data:**
  - Reads from `players.json` if it exists to prevent data duplication.

### 2. Crawling Data Sources

- **Fetch Main Data Page:**
  - Accesses the main league or category pages to gather links to individual team pages.
- **Extract Team URLs:**
  - Parses the HTML to find links to individual team pages.

### 3. Processing Each Team

- **Fetch Team Page:**
  - For each team URL, retrieves the team's page.
- **Extract Player URLs:**
  - Parses the team page to extract URLs of all players associated with the team.

### 4. Processing Each Player

- **Fetch Player Page:**
  - Accesses each player's individual page.
- **Extract Player Data:**
  - Parses the player page to extract:
    - **Name**
    - **Description**
    - **Biographical Information:** Including number, position, birth year, birth place, height, weight, team, status, nationality.
    - **Honors:** Achievements and awards.
- **Data Validation:**
  - Ensures that essential fields like `name` and `description` are populated.
  - Skips entries with placeholder descriptions to maintain data quality.
- **Save Data:**
  - Appends the extracted player data to `players.json`.
  - Periodically saves backups to prevent data loss.

### 5. Saving and Backing Up Data

- **Regular Saves:**
  - After extracting a defined number of players (`save_frequency`), the crawler saves the current data to `players.json`.
- **Backups:**
  - After reaching a backup threshold (`backup_frequency`), creates a backup copy of `players.json` in the `backups` directory.

### 6. Graceful Termination

- **Handling Interruptions:**
  - If the crawler is interrupted (e.g., via `Ctrl+C`), it ensures that any in-memory data is saved before exiting.

### 7. Logging

- **Detailed Logs:**
  - Throughout the crawling process, the crawler logs:
    - Successful data extractions.
    - Warnings for missing fields or unexpected HTML structures.
    - Errors encountered during HTTP requests or data parsing.

## LLM Integration

The **Sports Talk Application** employs a Retrieval-Augmented Generation (RAG) architecture to enhance the capabilities of its Language Learning Model (LLM). Here's how the integration works:

### 1. Document Retrieval

- **Embedding Generation:**
  - The crawler gathers and structures sports player data, which is then converted into embeddings using an embedding engine.
- **Vector Storage:**
  - Embeddings are stored in ChromaDB, a vector database optimized for similarity searches.

### 2. Query Processing

- **User Queries:**
  - Users interact with the application via the Backend API by submitting queries related to sports data.
- **Relevant Document Retrieval:**
  - The embedding engine processes the query to find the most relevant documents (player data) from ChromaDB based on embedding similarity.

### 3. Response Generation

- **Contextual Understanding:**
  - Retrieved documents provide context to the LLM, enabling it to generate more accurate and contextually relevant responses.
- **ChatGPT-3.5 Integration:**
  - The LLM utilizes both the retrieved data and its inherent language understanding to formulate expert-level responses tailored to user queries.

### 4. Continuous Learning

- **Data Updates:**
  - As new data is crawled and added to `players.json`, embeddings in ChromaDB are updated to reflect the latest information.
- **Scalability:**
  - The architecture supports the expansion of data sources and the integration of more sophisticated models to enhance expertise within the sports domain.

## Troubleshooting

- **Crawler Not Saving `players.json`:**
  - **Check Permissions:** Ensure that the application has write permissions to the `app/data` directory.
  - **Review Logs:** Examine console logs for any errors during the save process.
  - **Validate JSON Structure:** Ensure that `players.json` contains valid JSON. Use online validators if necessary.

- **Description Field Not Populating:**
  - **HTML Structure Changes:** The structure of the data source's player pages might have changed. Inspect the HTML of affected pages to adjust the extraction logic.
  - **Malformed Tags:** Handle any new types of malformed HTML tags that might interfere with parsing.

- **Docker Deployment Issues:**
  - **Image Build Errors:** Review the Docker build logs for any missing dependencies or syntax errors.
  - **Port Conflicts:** Ensure that the host port (80) isn't in use by another application.

- **Kubernetes Deployment Failures:**
  - **Resource Limits:** Verify that your cluster has sufficient resources to deploy the application.
  - **Service Accessibility:** Ensure that the service type (`ClusterIP`, `NodePort`, etc.) matches your access requirements.

## Contributing

Contributions are welcome! Please follow these steps:

1. **Fork the Repository:**

   Click the "Fork" button at the top-right corner of the repository page.

2. **Clone Your Fork:**

   ```bash
   git clone https://github.com/yourusername/sports-talk-app.git
   cd sports-talk-app
   ```

3. **Create a Feature Branch:**

   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make Your Changes:**

   Implement your feature or bug fix.

5. **Commit Your Changes:**

   ```bash
   git commit -m "Add feature: your feature description"
   ```

6. **Push to Your Fork:**

   ```bash
   git push origin feature/your-feature-name
   ```

7. **Submit a Pull Request:**

   Navigate to the original repository and click "New Pull Request."

## License

This project is licensed under the [MIT License](LICENSE).

---

## Additional Notes

- **Health Checks:**
  - The Kubernetes deployment includes readiness and liveness probes to ensure the application is running smoothly. Implement a `/health` endpoint in your FastAPI application to respond to these probes.

    ```python
    # main.py
    from fastapi import FastAPI

    app = FastAPI()

    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    ```

- **Monitoring and Logging:**
  - Consider integrating monitoring solutions like Prometheus and Grafana for real-time metrics.
  - Utilize centralized logging for easier log management and analysis.

- **Security Considerations:**
  - Secure your API endpoints with authentication and authorization mechanisms.
  - Ensure that sensitive information (e.g., API keys) is managed using environment variables or secret management tools.

- **Scalability:**
  - The application is designed to scale horizontally. Adjust the number of replicas in the Kubernetes deployment based on the load.

---