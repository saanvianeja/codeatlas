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
                dependencies.append((file.stem, imported_module))
    return {
        "dependencies": dependencies,
        #"files": dict_of_files,
        "results": results
    } 

if __name__ == "__main__":
    print(analyze_repo("sample_repo"))