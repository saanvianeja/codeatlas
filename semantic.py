from sentence_transformers import SentenceTransformer
from sentence_transformers import util 

model = SentenceTransformer("all-MiniLM-L6-v2")

def build_index(chunks):
    if chunks == []:
        return None
    code_strings = []
    for chunk in chunks:
        code_strings.append(chunk["code"])
    embeddings = model.encode(code_strings, convert_to_tensor=True)
    values = {
        "chunks":chunks, 
        "embeddings":embeddings
        }
    return values


def semantic_search(query, index, top_k=5): #index is values
    if not query or not(isinstance(query, str)):
        return None
    query_embedding = model.encode(query, convert_to_tensor=True)
    cosine_similarity = util.cos_sim(query_embedding, index["embeddings"])
    scores = cosine_similarity[0] #first row
    top_scores, top_indices = scores.topk(min(top_k, len(index["chunks"])))
    pairs = zip(top_scores, top_indices)
    result = []
    for pair in pairs:
        chunk = index["chunks"][pair[1]]
        result.append({"Name": chunk["name"], "Type": chunk["type"], "File": chunk["file"], "Code": chunk["code"], "Score": pair[0].item()})
    return result