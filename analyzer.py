from pathlib import Path
import ast
def analyze_file(file):
    code = file.read_text()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return {
            "file": file,
            "imports": [],
            "functions": [],
            "classes": [],
            "error": "SyntaxError"
        }
    imports = []
    functions = []
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append(node.name)
        elif isinstance(node, ast.Import):
            for name in node.names:
                imports.append(name.name)
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
    return {
        "imports": imports,
        "functions": functions,
        "classes": classes,
        "file": file
    }

def analyze_repo(folder):
    folder = Path(folder)
    python_files = folder.rglob("*.py")
    results = []
    for current_file in python_files:
        results.append(analyze_file(current_file))

    dict_of_files = {}
    for result in results:
        file = result["file"]
        dict_of_files[file.stem] = file

    dependencies = []
    for result in results:
        file = result["file"]
        imports = result["imports"]
        for imported_module in imports:
            if imported_module in dict_of_files:
                dependencies.append({
                    "source": file.stem,
                    "target": imported_module,
                })

    for result in results:
        result["file"] = str(result["file"].relative_to(folder))

    return {
        "dependencies": dependencies,
        #"files": dict_of_files,
        "files": results
    } 

def extract_code_chunks(file):
    code=file.read_text()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    lines = code.splitlines()
    chunks = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = node.lineno - 1
            end = node.end_lineno
            chunk_code = "\n".join(lines[start:end])
            chunks.append({
                "name": node.name,
                "type": type(node).__name__,
                "file": str(file),
                "code": chunk_code
            })
    return chunks

def extract_repo_chunks(folder):
    all_chunks = []
    folder = Path(folder)
    python_files = folder.rglob("*.py")

    for file in python_files:
        file_chunks = extract_code_chunks(file)

        for chunk in file_chunks:
            chunk["file"] = str(file.relative_to(folder))

        all_chunks.extend(file_chunks)

    return all_chunks
    
if __name__ == "__main__":
    print(analyze_repo("sample_repo"))