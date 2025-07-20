from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from agent.agentic import process_court_order
import fitz  # PyMuPDF
import sys
import os
# Add the project root (parent of backend/) to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

app = FastAPI()

def extract_text_from_pdf(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

@app.post("/process_doc")
async def process_doc(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    try:
        text = extract_text_from_pdf(file.file)
        state = process_court_order(text)

        return JSONResponse(content={
            "filename": file.filename,
            "national_id": state.get("national_id"),
            "action": state.get("action"),
            "llm_response": state.get("llm_response"),
            "status": state.get("status"),
            "customer_id": state.get("customer_id"),
            "result": state.get("result"),
            "error": state.get("error")
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")
