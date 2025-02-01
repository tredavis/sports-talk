# main.py

import os
import json
import re
import traceback
from typing import Dict
from urllib.parse import urljoin
from datetime import datetime

import openai
import torch
import torch.nn.functional as F
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel, AutoModelForCausalLM
import chromadb
from chromadb.utils import embedding_functions
from fastapi.middleware.cors import CORSMiddleware

from bs4 import BeautifulSoup

# Optional: If using a .env file, uncomment the following lines
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Sports Talk RAG Demo")

# Allow CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Adjust according to frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)  # Prometheus monitoring instrumentation

# Initialize OpenAI API Key
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError(
        "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable."
    )
openai.api_key = openai_api_key


def get_embeddings(text, model, tokenizer):
    # Tokenize and get model outputs
    inputs = tokenizer(
        text, return_tensors="pt", padding=True, truncation=True, max_length=512
    )
    with torch.no_grad():  # Disable gradient calculation
        outputs = model(**inputs)
        # Use mean pooling
        embeddings = outputs.last_hidden_state.mean(dim=1)  # Shape: [1, 768]

        # Reshape for avg_pool1d
        embeddings = embeddings.unsqueeze(0)  # Shape: [1, 1, 768]
        # Reduce from 768 to 384 dimensions
        embeddings = F.avg_pool1d(embeddings, kernel_size=2)  # Shape: [1, 1, 384]

        return embeddings.squeeze().numpy().tolist()  # Final shape: [384]


def load_players_from_json():
    """Load player data from JSON file"""
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    players_file = os.path.join(data_dir, "players.json")

    if os.path.exists(players_file):
        with open(players_file, "r") as f:
            data = json.load(f)
            # Make sure we're returning the list of players from the JSON structure
            return data.get("players", [])
    return []


@app.on_event("startup")
async def startup_event():
    global embedder_tokenizer, embedder_model, chroma_client, collection
    global llm_model, llm_tokenizer

    # 1. Initialize embedding model
    embedder_tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
    embedder_model = AutoModel.from_pretrained("bert-base-uncased")

    # 2. Set up Chroma
    chroma_client = chromadb.PersistentClient(path=".chroma")
    try:
        chroma_client.delete_collection(name="sports")
        print("Deleted existing collection")
    except Exception as e:
        print(f"No existing collection to delete: {e}")
    collection = chroma_client.get_or_create_collection(name="sports")

    # Load players from JSON
    players = load_players_from_json()
    print(f"\nLoaded {len(players)} players from JSON")

    # Convert to documents format
    docs = []
    ids = []
    seen_names = set()

    for idx, player in enumerate(players):
        # Only process if we have a description and it's not a placeholder
        description = player.get("description", "").strip()
        if description and description != "--- add one?":
            # Extract name from description (usually first sentence up to first parenthesis)
            name_match = re.match(r"^([^(]+)", description)
            if name_match:
                name = name_match.group(1).strip()
                print(f"\nProcessing player {idx + 1}/{len(players)}")
                print(f"Extracted Name: {name}")
                print(f"Description length: {len(description)}")

                # Create unique ID using extracted name
                unique_id = f"{name}_{idx}"  # Using index to ensure uniqueness

                if unique_id in seen_names:
                    print(f"Skipping duplicate player: {unique_id}")
                    continue

                seen_names.add(unique_id)

                # Add to documents
                docs.append(description)
                ids.append(unique_id)
                print(f"Added player: {unique_id}")
        else:
            print(
                f"\nSkipping player {idx + 1} - no description or placeholder description"
            )

    # Generate embeddings
    if docs:
        print(f"\nProcessing {len(docs)} unique players...")
        embeddings = [
            get_embeddings(doc, embedder_model, embedder_tokenizer) for doc in docs
        ]

        # Add to collection
        collection.add(documents=docs, embeddings=embeddings, ids=ids)
        print(f"Added {len(docs)} players to vector database")
    else:
        print("No players to add to vector database!")

    # 3. Initialize LLM (Removed local LLM initialization)

    # 4. Prometheus monitoring instrumentation


class QueryRequest(BaseModel):
    question: str


@app.post("/ask")
async def ask_question(query_req: QueryRequest):
    print("\n" + "=" * 50)
    print(f"📝 Question: {query_req.question}")
    print("-" * 50)

    # Convert user question into embedding
    query_embedding = get_embeddings(
        query_req.question, embedder_model, embedder_tokenizer
    )

    # Retrieve matching docs (increase n_results since we're looking for multiple players)
    results = collection.query(query_embeddings=[query_embedding], n_results=10)
    retrieved_docs = results["documents"][0]
    retrieved_ids = results["ids"][0]

    # print("🔍 Retrieved Context:")
    # for i, (doc, id) in enumerate(zip(retrieved_docs, retrieved_ids), 1):
    #     print(f"\n{i}. {id}: {doc[:200]}...")

    # Combine retrieved documents into a single context string
    context = "\n\n".join(retrieved_docs)

    # Create a prompt for OpenAI
    prompt = f"""
    You are an intelligent assistant knowledgeable about NFL players.

    Use the information below to answer the question.

    Context:
    {context}

    Question: {query_req.question}

    Answer:
    """

    try:
        # Call OpenAI API to generate the answer
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an intelligent assistant knowledgeable about NFL players. Only answer questions about the NFL. If the question is not about the NFL, say 'I'm sorry, but I can only answer questions about the NFL.'",
                },
                {
                    "role": "user",
                    "content": f"Use the following context to answer the question like you are a sports expert.\n\nContext:\n{context}\n\nQuestion: {query_req.question}",
                },
            ],
            max_tokens=300,
            n=1,
            stop=None,
            temperature=0.7,
        )

        answer = response.choices[0].message["content"].strip()
        print(f"💡 Answer: {answer}")
    except Exception as e:
        print(f"Error contacting OpenAI API: {e}")
        answer = "I'm sorry, but I couldn't process your request at the moment."

    print("=" * 50 + "\n")

    return {"question": query_req.question, "answer": answer}


@app.get("/health")
async def health():
    return {"status": "healthy"}


def create_sports_docs():
    """Create document objects from sports data files"""
    docs = []

    # Load players data
    try:
        with open("app/data/players.json", "r") as f:
            players_data = json.load(f)
            players = players_data.get("players", [])

            for player in players:
                if not isinstance(player, dict):
                    print(f"Skipping invalid player data: {player}")
                    continue

                description = player.get("description", "").strip()

                # Skip players with placeholder description
                if description == "--- add one?":
                    print(
                        f"Skipping player '{player.get('name', 'Unknown')}' due to placeholder description."
                    )
                    continue

                # Create document for each player
                doc = {
                    "title": player.get("name", "Unknown Player"),
                    "content": description,
                    "metadata": {
                        "url": player.get("url", ""),
                        "team": player.get("team", ""),
                        "position": player.get("position", ""),
                        "nationality": player.get("nationality", ""),
                        "honors": player.get("honors", []),
                    },
                }
                docs.append(doc)

    except Exception as e:
        print(f"Error loading players data: {e}")
        traceback.print_exc()

    return docs


def update_sample_data(sports_docs):
    """Update sample_data.py with new sports docs"""
    print("\nUpdating sample_data.py...")
    sample_data_path = os.path.join(os.path.dirname(__file__), "sample_data.py")

    # Read existing SPORTS_DOCS if file exists
    existing_docs = []
    if os.path.exists(sample_data_path):
        with open(sample_data_path, "r") as f:
            content = f.read()
            try:
                # Find the list content between brackets
                start = content.find("[")
                end = content.rfind("]") + 1
                if start != -1 and end != -1:
                    existing_docs = eval(content[start:end])
            except Exception as e:
                print(f"Error reading existing sample_data.py: {e}")

    # Merge existing docs with new docs, avoiding duplicates
    updated_docs = existing_docs.copy()
    for new_doc in sports_docs:
        if not any(doc["title"] == new_doc["title"] for doc in existing_docs):
            updated_docs.append(new_doc)
            print(f"Added {new_doc['title']} to sample_data.py")

    # Write back to file
    with open(sample_data_path, "w") as f:
        f.write("# sample_data.py\n\nSPORTS_DOCS = ")
        f.write(json.dumps(updated_docs, indent=4))

    print(f"Successfully updated {sample_data_path}")
    return updated_docs


def update_vector_db():
    """Update the vector database with player data"""
    # Initialize ChromaDB
    chroma_client = chromadb.Client()

    # Get or create collection
    try:
        collection = chroma_client.get_collection("players")
        print("Found existing collection")
    except:
        collection = chroma_client.create_collection("players")
        print("Created new collection")

    # Convert player data to SPORTS_DOCS format
    sports_docs = create_sports_docs()

    # Update sample_data.py
    update_sample_data(sports_docs)

    # Process each document
    for doc in sports_docs:
        try:
            collection.add(
                documents=[doc["content"]],
                metadatas=[
                    {
                        "title": doc["title"],
                        "url": doc["metadata"]["url"],
                        "team": doc["metadata"]["team"],
                        "position": doc["metadata"]["position"],
                        "nationality": doc["metadata"]["nationality"],
                        "honors": doc["metadata"]["honors"],
                    }
                ],
                ids=[doc["title"]],
            )
            print(f"Added {doc['title']} to vector database")
        except Exception as e:
            print(f"Error adding {doc['title']}: {e}")


if __name__ == "__main__":
    print("Starting updates...")
    update_vector_db()
    print("Updates complete!")


