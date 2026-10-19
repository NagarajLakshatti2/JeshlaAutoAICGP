"""Optional local-only semantic ranking of scoped SQLite facts."""
from functools import lru_cache
import json
import math
import os

@lru_cache(maxsize=1)
def load_encoder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(os.getenv("AI_MEMORY_EMBEDDING_MODEL","sentence-transformers/all-MiniLM-L6-v2"),device="cpu",local_files_only=True,trust_remote_code=False)

def rank_facts(rows,query,limit,*,encoder=None,min_score=0.35):
    encoder=encoder if encoder is not None else load_encoder()
    texts=[query[:1500]]+[row["key"]+" "+json.dumps(row["value"],ensure_ascii=False)[:2000] for row in rows]
    vectors=encoder.encode(texts,normalize_embeddings=True,show_progress_bar=False)
    if len(vectors)!=len(texts):raise ValueError("Embedding count mismatch")
    query_vector=list(vectors[0]);ranked=[]
    for row,vector in zip(rows,vectors[1:]):
        if len(vector)!=len(query_vector):raise ValueError("Embedding dimensions mismatch")
        score=sum(float(a)*float(b) for a,b in zip(query_vector,vector))
        if not math.isfinite(score):raise ValueError("Invalid embedding score")
        if score>=min_score:ranked.append({**row,"semantic_score":round(score,6)})
    ranked.sort(key=lambda row:(-row["semantic_score"],row["key"]))
    return ranked[:limit]
