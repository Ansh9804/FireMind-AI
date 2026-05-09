import json
import logging
import io
import httpx
import os
from typing import AsyncGenerator, List, Dict
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from pypdf import PdfReader
from openai import AsyncOpenAI

# 🔥 FIXED: Imported semantic_chunk_text instead of chunk_text
from backend.embeddings import build_index, create_embeddings, semantic_chunk_text, save_index
from backend.retrieval import retrieve_context
from backend.web_search import search_web
from backend.app_config import BASE_DIR

# ================= CONFIG & LOGGING ================= #
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="FireMind AI API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= STATE INITIALIZATION ================= #
try:
    logger.info("Initializing vector index...")
    index, texts = build_index()
except Exception as e:
    logger.error(f"Failed to load vector index: {e}")
    index, texts = None, []

# ================= MODELS ================= #
class Query(BaseModel):
    message: str
    history: List[Dict[str, str]] = [] 


def format_history(history: List[Dict[str, str]]) -> str:
    if not history:
        return "No previous conversation."
    
    recent_history = history[-5:]
    formatted = ""
    for msg in recent_history:
        role = "User" if msg["role"] == "user" else "FireMind"
        formatted += f"{role}: {msg['content']}\n"
    return formatted

# ================= AI QUERY REWRITER ================= #
async def generate_optimized_query(user_message: str, history_text: str) -> str:
    prompt = f"""
    You are an AI that extracts the core search query from a user's message.
    Your task is to take the user's latest message and rewrite it into a concise search engine query (max 5 words).
    
    Respond ONLY with the raw search query string. Do not include quotes, prefixes, or conversational text.

    --- Conversation History ---
    {history_text}

    --- User Message ---
    {user_message}

    Optimized Search Query:
    """

    try:
        response = await client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )
        optimized_query = response.choices[0].message.content.strip()
        
        if not optimized_query or len(optimized_query) > 200:
            return user_message
        return optimized_query
    except Exception as e:
        logger.error(f"Query rewriter failed: {e}")
        return user_message

# ================= ENDPOINTS ================= #
@app.post("/chat")
async def chat(query: Query):
    context, web_context = "", ""
    chat_history = format_history(query.history)
    
    is_small_talk = len(query.message.split()) < 4 and any(word in query.message.lower() for word in ["hi", "hello", "hey", "thanks", "bye"])
    
    # Even for small talk, we want to retrieve general context so it doesn't hallucinate missing info
    # if it decides to introduce itself. We will use a generic search query for small talk.
    if is_small_talk:
        search_query = "FERL IIT Gandhinagar contact information address"
    else:
        search_query = await generate_optimized_query(query.message, chat_history)
        
    logger.info(f"Original: '{query.message}' | Optimized: '{search_query}'")

    try:
        context_chunks = await run_in_threadpool(retrieve_context, search_query, index, texts)
        context = "\n\n".join(context_chunks) if isinstance(context_chunks, list) else context_chunks
        web_context = await run_in_threadpool(search_web, search_query)
    except Exception as e:
        logger.error(f"Retrieval error: {e}")

    prompt = f"""Instruct: You are FireMind, the official AI assistant for the Fire Engineering Research Laboratory (FERL) at IIT Gandhinagar. Respond in a highly professional, clear, and structured manner.
If the user is just saying hello, greet them back and provide your location/contact info using the Context below.
Answer the user's message directly and naturally based ONLY on the provided Context. 
CRITICAL RULES:
- When providing contact information, links, addresses, or pin codes from the Context, quote them EXACTLY as they appear. 
- Do NOT use placeholders like [Address: 382055] or [Phone number] or [Website URL]. Use the actual data from the Context.
- Do NOT hallucinate or alter numbers.
- Do NOT generate hypothetical scenarios, do NOT ask yourself questions, and do NOT include the word "FireMind:" in your response. 
Just provide the exact answer to the user.

Context:
{context if context else 'No additional context.'}
{web_context if web_context else ''}

Conversation History:
{chat_history}
User: {query.message}
FireMind:"""

    async def generate_stream() -> AsyncGenerator[str, None]:
        try:
            stream = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                stream=True
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield "\n\n⚠️ **Error:** An unexpected error occurred while generating the response."

    return StreamingResponse(generate_stream(), media_type="text/plain")


def process_pdf_and_embed(file_content: bytes):
    reader = PdfReader(io.BytesIO(file_content))
    full_text = "".join([page.extract_text() + "\n" for page in reader.pages if page.extract_text()])
            
    # 🔥 FIXED: Using the new semantic chunker here
    chunks = semantic_chunk_text(full_text)
    if not chunks: return [], None
        
    embeddings = create_embeddings(chunks)
    return chunks, embeddings


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    global index, texts
    
    try:
        file_content = await file.read()
        chunks, embeddings = await run_in_threadpool(process_pdf_and_embed, file_content)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="Could not extract text.")

        texts.extend(chunks)
        index.add(embeddings)
        
        await run_in_threadpool(save_index, index, texts)

        return {"message": "PDF indexed successfully", "chunks": len(chunks)}
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Error processing PDF.")

# Mount the static frontend
web_path = os.path.join(BASE_DIR, "web")
app.mount("/", StaticFiles(directory=web_path, html=True), name="web")