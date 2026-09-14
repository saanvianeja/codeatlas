import analyzer
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import tempfile
from fastapi.middleware.cors import CORSMiddleware
import semantic

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
current_index = None
class AnalysisRequest(BaseModel):
    repo_url: str
class SemanticSearch(BaseModel):
    query: str
#query parameter = has the parameter passed in the URL, so /analyze?folder=sample_repo 
#path parameter = value built into URL path, so /analyze/sample_repo
#request body = http request can cary a body as JSON, so url stays /analyze, input is carried in request
#get = give some information 
@app.get("/")
def root():
    return {"message": "Hello World"}
@app.post("/analyze")
def analyze(request: AnalysisRequest):
    global current_index 

    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(["git","clone", request.repo_url, temp_dir], check=True)
        analysis = analyzer.analyze_repo(temp_dir)
        chunks = analyzer.extract_repo_chunks(temp_dir)
        current_index = semantic.build_index(chunks)
    
    return analysis
#post = send data/info to process, trigger an operation 
@app.post("/semantic_search")
def semantic_search(request: SemanticSearch):
    if current_index is None:
        return {"error": "Analyze a repository before using semantic search."}

    return semantic.semantic_search(
        request.query,
        current_index
    )
