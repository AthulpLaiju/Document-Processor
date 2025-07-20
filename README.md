**Court Order PDF Processor**

This project processes scanned court order PDFs using OCR and AI to extract important fields like National ID and Action. It validates the extracted data and decides whether to execute or discard the request. The system uses OpenAI or Falcon models and LangGraph for automated decision-making.

**Project Features**

Accepts scanned PDF court orders

Extracts raw text using OCR with PyMuPDF

Extracts fields using LLMs like OpenAI 

Validates National ID and Action using CSV files

Executes or discards based on validation outcome

Uses LangGraph for workflow automation

Built with FastAPI backend and Streamlit frontend

**Technology Stack**

Python 3.10

PyMuPDF for PDF OCR

OpenAI for field extraction

LangGraph for workflow handling

FastAPI as backend server

Streamlit as frontend interface


**Setup Instructions**
Clone the repository:
git clone https://github.com/yourusername/pdf-court-order-processor.git
cd pdf-court-order-processor

Install required dependencies:
pip install -r requirements.txt

Make sure Python version is 3.10 or higher

Running the Application
Start backend API:

cd backend  
command:uvicorn app:app --reload
Start Streamlit frontend:streamlit run frontend_app.py
