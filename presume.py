import os
import requests
import shutil
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from tempfile import NamedTemporaryFile
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# FastAPI app
app = FastAPI()

# HTML for file upload
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Resume Rating</title>
    <script>
        function showLoader() {
            document.getElementById("loader").style.display = "block";
        }
    </script>
</head>
<body>
    <h2>Upload Your Resume (PDF only)</h2>
    <form action="/rate-resume/" enctype="multipart/form-data" method="post" onsubmit="showLoader()">
        <input type="file" name="file" accept=".pdf" required>
        <button type="submit">Upload & Rate</button>
    </form>
    <div id="loader" style="display: none;">Processing... Please wait.</div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def upload_form():
    return HTML_TEMPLATE

@app.post("/rate-resume/")
async def rate_resume(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Only PDF files are allowed"})

    # Save uploaded file temporarily
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        shutil.copyfileobj(file.file, temp_file)
        temp_path = temp_file.name

    # Mock PDF text extraction (replace with real extraction)
    text_content = f"Extracted text from {file.filename} (mocked for now)"

    # Call Groq API for resume rating
    ai_response = call_groq_api(text_content)

    # Delete temp file
    os.remove(temp_path)

    return ai_response

def call_groq_api(text):
    """
    Calls Groq API to analyze the resume and return structured JSON output.
    """
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "system", "content": "You are an AI resume reviewer. Provide output **strictly in JSON format**."},
            {"role": "user", "content": f"Analyze the following resume and return a JSON response with:\n"
                                        "1. 'rating' (integer, from 1 to 10)\n"
                                        "2. 'positives' (list of 3 strings)\n"
                                        "3. 'negatives' (list of 3 strings)\n"
                                        "4. 'improvement_scope' (list of 3 strings)\n"
                                        "Ensure the response is **valid JSON only**, with no extra text.\n\n"
                                        "Resume:\n" + text}
        ],
        "temperature": 0.7
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        return parse_ai_response(content)
    else:
        return {"error": response.json()}

def parse_ai_response(content):
    """
    Parses AI response, ensuring it's valid JSON.
    """
    try:
        # Ensure JSON response is directly returned
        return eval(content)  # Use `json.loads(content)` if response is proper JSON
    except Exception as e:
        return {
            "rating": "N/A",
            "positives": ["Could not extract data"],
            "negatives": ["Could not extract data"],
            "improvement_scope": ["Could not extract data"],
            "error": str(e)
        }
