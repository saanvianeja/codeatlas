import analyzer
from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import tempfile

app = FastAPI()
class AnalysisRequest(BaseModel):
    repo_url: str
#query parameter = has the parameter passed in the URL, so /analyze?folder=sample_repo 
#path parameter = value built into URL path, so /analyze/sample_repo
#request body = http request can cary a body as JSON, so url stays /analyze, input is carried in request
#get = give some information 
@app.get("/")
def root():
    return {"message": "Hello World"}
@app.post("/analyze")
def analyze(request: AnalysisRequest):
    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(["git","clone", request.repo_url, temp_dir], check=True)
        return analyzer.analyze_repo(temp_dir)
#post = send data/info to process, trigger an operation 
