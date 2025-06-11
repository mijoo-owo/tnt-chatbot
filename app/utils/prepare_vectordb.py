# utils/prepare_vectordb.py

import os
import shutil
from typing import List
import streamlit as st
import hashlib

from dotenv import load_dotenv
import chromadb
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
    UnstructuredWordDocumentLoader
)
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.docstore.document import Document

# --- Constants ---
DEFAULT_DOCS_DIR    = "docs"
DEFAULT_PERSIST_DIR = "Vector_DB - Documents"
DEFAULT_CHUNKS_DIR  = "chunks"
CHUNK_SIZE          = 8000
CHUNK_OVERLAP       = 800

# Load your .env (must contain OPENAI_API_KEY)
load_dotenv()

def has_new_files(persist_dir: str, current_files: List[str]) -> bool:
    cache_path = os.path.join(persist_dir, "files.txt")
    if not os.path.exists(cache_path):
        return True
    with open(cache_path, "r", encoding="utf-8") as f:
        cached_files = set(line.strip() for line in f.readlines())
    return set(current_files) != cached_files

def extract_text(file_list: List[str], docs_dir: str = DEFAULT_DOCS_DIR):
    docs = []
    for fn in file_list:
        path = os.path.join(docs_dir, fn)
        try:
            if fn.lower().endswith(".pdf"):
                docs.extend(PyPDFLoader(path).load())
            elif fn.lower().endswith(".txt"):
                docs.extend(TextLoader(path, encoding="utf-8").load())
            elif fn.lower().endswith(".docx"):
                docs.extend(Docx2txtLoader(path).load())
            elif fn.lower().endswith(".doc"):
                docs.extend(UnstructuredWordDocumentLoader(path).load())
            else:
                st.warning(f"⚠️ Unsupported file type: {fn}")
        except Exception as e:
            st.error(f"❌ Failed to process {fn}: {e}")
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

def save_text_chunks(
    chunks,
    chunks_dir: str = DEFAULT_CHUNKS_DIR,
    overwrite: bool = True
) -> None:
    if overwrite and os.path.isdir(chunks_dir):
        shutil.rmtree(chunks_dir)
    os.makedirs(chunks_dir, exist_ok=True)

    for i, chunk in enumerate(chunks):
        src = chunk.metadata.get("source", "")
        base = os.path.splitext(os.path.basename(src))[0] if src else "doc"
        fname = f"{base}_chunk_{i:04d}.txt"
        path = os.path.join(chunks_dir, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(chunk.page_content)

    print(f"✅ Exported {len(chunks)} chunks to '{chunks_dir}/'")
    
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_vectorstore(
    file_list: List[str],
    docs_dir: str = DEFAULT_DOCS_DIR,
    persist_dir: str = DEFAULT_PERSIST_DIR,
    chunks_dir: str = DEFAULT_CHUNKS_DIR
) -> Chroma:
    """
    Incrementally update a Chroma vectorstore by embedding only new files.
    """
    embedding = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    # Load or create vectorstore
    vectordb = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding
    )

    # Load previously embedded file list
    cache_path = os.path.join(persist_dir, "files.txt")
    prev_files = set()
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            prev_files = set(line.strip() for line in f)

    # Filter new files
    new_files = [f for f in file_list if f not in prev_files]
    if not new_files:
        print("✅ No new files to add.")
        return vectordb

    print(f"🆕 New files to process: {new_files}")
    docs = extract_text(new_files, docs_dir)
    chunks = get_text_chunks(docs)

    # Deduplicate by chunk content hash
    seen_hashes = set()
    unique_chunks: List[Document] = []
    for chunk in chunks:
        content_hash = hash_text(chunk.page_content)
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_chunks.append(chunk)

    # Add only unique chunks
    if unique_chunks:
        vectordb.add_documents(unique_chunks)
        vectordb.persist()
        print(f"✅ Added {len(unique_chunks)} unique chunks.")
    else:
        print("⚠️ No unique chunks to embed — skipping update.")

    # Append new files to file cache
    with open(cache_path, "a", encoding="utf-8") as f:
        for fname in new_files:
            f.write(fname + "\n")

    # Save new chunks for inspection
    save_text_chunks(unique_chunks, chunks_dir=chunks_dir, overwrite=False)

    return vectordb
