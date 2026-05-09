from backend.router import decide_source
from backend.web_search import search_web


@app.post("/chat")
def chat(query: Query):

    source = decide_source(query.message)

    local_context = ""
    web_context = ""

    # 🔍 LOCAL RAG
    if source in ["local", "hybrid"]:
        local_context = retrieve_context(query.message, index, texts)

        if isinstance(local_context, list):
            local_context = "\n\n".join(local_context)

    # 🌐 WEB SEARCH
    if source in ["web", "hybrid"]:
        web_context = search_web(query.message)

    # 🧠 COMBINE CONTEXT
    combined_context = f"""
Local Knowledge:
{local_context}

Web Knowledge:
{web_context}
"""

    personality = get_personality_prompt(query.mode)

    prompt = f"""
You are FireMind AI.

{personality}

Instructions:
- Decide which knowledge is more relevant
- Prefer web for recent information
- Prefer local for domain-specific knowledge
- Combine both when useful

Context:
{combined_context}

Question:
{query.message}

Answer:
"""

    def stream():
        try:
            with requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "phi3",
                    "prompt": prompt,
                    "stream": True
                },
                stream=True
            ) as r:

                for line in r.iter_lines():
                    if line:
                        data = json.loads(line.decode())
                        yield data.get("response", "")

        except Exception:
            yield "⚠️ LLM error"

    return StreamingResponse(stream(), media_type="text/plain")