# utils/prepare_vectordb.py

import os
import shutil
from typing import List
import streamlit as st

from dotenv import load_dotenv
import chromadb
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# --- Constants ---
DEFAULT_DOCS_DIR    = "docs"
DEFAULT_PERSIST_DIR = "Vector_DB - Documents"
DEFAULT_CHUNKS_DIR  = "chunks"
CHUNK_SIZE          = 8000
CHUNK_OVERLAP       = 800

# Load your .env (must contain OPENAI_API_KEY)
load_dotenv()

def extract_pdf_text(
    pdf_filenames: List[str],
    docs_dir: str = DEFAULT_DOCS_DIR
):
    docs = []
    for fn in pdf_filenames:
        path = os.path.join(docs_dir, fn)
        docs.extend(PyPDFLoader(path).load())
    return docs

def get_text_chunks(
    docs,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(docs)

def save_pdf_chunks(
    pdf_filenames: List[str],
    docs_dir: str = DEFAULT_DOCS_DIR,
    chunks_dir: str = DEFAULT_CHUNKS_DIR,
    overwrite: bool = True
) -> None:
    if overwrite and os.path.isdir(chunks_dir):
        shutil.rmtree(chunks_dir)
    os.makedirs(chunks_dir, exist_ok=True)

    docs   = extract_pdf_text(pdf_filenames, docs_dir)
    chunks = get_text_chunks(docs)

    for i, chunk in enumerate(chunks):
        src   = chunk.metadata.get("source", "")
        base  = os.path.splitext(os.path.basename(src))[0] if src else "doc"
        fname = f"{base}_chunk_{i:04d}.txt"
        path  = os.path.join(chunks_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(chunk.page_content)

    print(f"✅ Exported {len(chunks)} chunks to '{chunks_dir}/'")

def get_vectorstore(
    pdf_filenames: List[str],
    from_session_state: bool = False
) -> Chroma:
    """
    Create or load a Chroma vectorstore for the given PDFs,
    and always export the text chunks to disk.
    """
    # 1) Prepare OpenAI embeddings
    embedding = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    # 2) Try loading existing store
    vectordb = None
    if from_session_state and os.path.isdir(DEFAULT_PERSIST_DIR):
        try:
            vectordb = Chroma(
                persist_directory=DEFAULT_PERSIST_DIR,
                embedding_function=embedding,
            )
        except chromadb.errors.InvalidArgumentError:
            shutil.rmtree(DEFAULT_PERSIST_DIR)

    # 3) Build from scratch if needed
    if vectordb is None:
        docs = extract_pdf_text(pdf_filenames)
        chunks = get_text_chunks(docs)
        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=embedding,
            persist_directory=DEFAULT_PERSIST_DIR
        )

    # 4) Export chunks on every call
    save_pdf_chunks(pdf_filenames)

    return vectordb
