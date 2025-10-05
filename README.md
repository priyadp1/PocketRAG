# PocketRAG: Lightweight Document-Based Q&A App

PocketRAG is a minimal Retrieval-Augmented Generation (RAG) web application that allows users to upload documents (PDF, TXT, MD) and instantly receive summaries and AI-powered answers using Google’s Gemini-2.5-Flash model.  
The app is containerized using Docker and deployed on AWS EC2, utilizing Gunicorn for production reliability.

---


**URL:** http://98.84.99.212/

---

## Tech Stack

| Layer | Technologies |
|-------|---------------|
| Frontend/UI | HTML, CSS |
| Backend | Flask, Gunicorn |
| Vector Store | FAISS |
| AI Model | Google Generative AI (Gemini-2.5-Flash) |
| Environment Management | Python-dotenv |
| Containerization | Docker |
| Cloud Hosting | AWS EC2 (Ubuntu 24.04, t2.micro) |

---

## Project Structure
HackRU2025/
│
├── app.py # Main Flask app
├── requirements.txt # Python dependencies
├── Dockerfile # Docker image definition
├── static/ # CSS and client-side assets
├── templates/ # HTML templates
├── .env.example # Example environment variables
└── README.md


---

## Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/priyadp1/PocketRAG.git
   cd PocketRAG


Create a virtual environment

python3 -m venv venv
source venv/bin/activate


Install dependencies

pip install -r requirements.txt


Set up environment variables

GOOGLE_API_KEY=your_api_key_here
GENAI_MODEL=gemini-2.5-flash
PORT=5050


Run locally

python3 app.py


Docker Deployment
Build the image
docker build -t pocketrag .

Run the container
docker run -d --name pocketrag \
  -p 80:5050 \
  -e GOOGLE_API_KEY="your_api_key_here" \
  -e GENAI_MODEL="gemini-2.5-flash" \
  --restart=always \
  pocketrag



AWS EC2 Deployment

Launch an Ubuntu 24.04 EC2 instance

Type: t3.small

Security groups:

HTTP (TCP 80 → 0.0.0.0/0)

SSH (TCP 22 → your_ip/32)

SSH into the instance

ssh -i ~/Downloads/hehe.pem ubuntu@<your-ec2-ip>


Install Docker

sudo apt update
sudo apt install docker.io -y


Transfer your project

scp -i ~/Downloads/hehe.pem -r ~/HackRU2025 ubuntu@<your-ec2-ip>:~


Build and run the container

cd ~/HackRU2025
docker build -t pocketrag .
docker run -d --name pocketrag \
  -p 80:5050 \
  -e GOOGLE_API_KEY="your_api_key_here" \
  -e GENAI_MODEL="gemini-2.5-flash" \
  --restart=always \
  pocketrag


Verify the app is running

curl -i http://127.0.0.1/health


Response:

{"ok": true}

Features

Upload documents in PDF, TXT, or MD format

Automatic document chunking and embedding with FAISS

Query answering using Gemini-2.5-Flash

Stateless per-document indexing

Simple Flask-based UI

Dockerized and production-ready with Gunicorn

Environment Variables
Variable	Description
GOOGLE_API_KEY	Your Gemini API key
GENAI_MODEL	Model name (default: gemini-2.5-flash)
PORT	Flask port (default: 5050)
Health Check

Check container status:

docker ps


Verify health endpoint:

curl -i http://127.0.0.1/health
