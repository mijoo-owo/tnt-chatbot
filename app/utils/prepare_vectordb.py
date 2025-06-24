# utils/prepare_vectordb.py

import os
import shutil
from typing import List
import streamlit as st
import hashlib
import pandas as pd
import re
import fitz  # PyMuPDF for PDF image extraction
from paddleocr import PaddleOCR

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
from langchain_openai import OpenAIEmbeddings
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

def is_gibberish(text, threshold=0.3):
    if not text:
        return True
    alnum = sum(c.isalnum() for c in text)
    ratio = alnum / max(len(text), 1)
    return ratio < threshold

def ocr_pdf_with_paddleocr(pdf_path, lang='vi'):  # Vietnamese support
    ocr = PaddleOCR(lang=lang, use_angle_cls=True, show_log=False)
    doc = fitz.open(pdf_path)
    all_text = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        images = page.get_images(full=True)
        page_text = []
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            import numpy as np
            import cv2
            img_array = np.frombuffer(image_bytes, np.uint8)
            img_cv = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            if img_cv is not None:
                result = ocr.ocr(img_cv, cls=True)
                for line in result:
                    for box in line:
                        text = box[1][0]
                        page_text.append(text)
        # If no images, try to render the page as an image and OCR it
        if not images:
            pix = page.get_pixmap()
            img_cv = np.frombuffer(pix.samples, dtype=np.uint8).reshape((pix.height, pix.width, pix.n))
            result = ocr.ocr(img_cv, cls=True)
            for line in result:
                for box in line:
                    text = box[1][0]
                    page_text.append(text)
        if page_text:
            all_text.append(f"Page {page_num+1}:\n" + "\n".join(page_text))
    doc.close()
    if all_text:
        return [Document(page_content="\n\n".join(all_text), metadata={"source": pdf_path})]
    return []

def extract_text(file_list: List[str], docs_dir: str = DEFAULT_DOCS_DIR):
    docs = []
    for fn in file_list:
        path = os.path.join(docs_dir, fn)
        try:
            if fn.lower().endswith(".pdf"):
                loaded = PyPDFLoader(path).load()
                all_text = " ".join(doc.page_content for doc in loaded)
                if not loaded or is_gibberish(all_text):
                    st.warning(f"⚠️ Falling back to PaddleOCR for: {fn}")
                    try:
                        ocr_loaded = ocr_pdf_with_paddleocr(path, lang='vi')
                        docs.extend(ocr_loaded)
                    except Exception as ocr_e:
                        continue
                else:
                    docs.extend(loaded)
            elif fn.lower().endswith(".txt"):
                docs.extend(TextLoader(path, encoding="utf-8").load())
            elif fn.lower().endswith(".docx"):
                docs.extend(Docx2txtLoader(path).load())
            elif fn.lower().endswith(".doc"):
                docs.extend(UnstructuredWordDocumentLoader(path).load())
            elif fn.lower().endswith(".xls") or fn.lower().endswith(".xlsx"):
                # Excel support for both .xls and .xlsx, with engine selection
                try:
                    if fn.lower().endswith(".xls"):
                        df = pd.read_excel(path, sheet_name=None, engine="xlrd")
                    else:
                        df = pd.read_excel(path, sheet_name=None, engine="openpyxl")
                except Exception as e:
                    # Fallback to default engine if specified engine fails
                    try:
                        df = pd.read_excel(path, sheet_name=None)
                    except Exception as e2:
                        continue
                text = ""
                for sheet, data in df.items():
                    text += f"Sheet: {sheet}\n"
                    text += data.to_string(index=False)
                    text += "\n\n"
                if text.strip():
                    docs.append(Document(page_content=text, metadata={"source": path}))
            else:
                st.warning(f"⚠️ Unsupported file type: {fn}")
        except Exception as e:
            continue
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

def load_custom_chunks(chunks_dir: str = DEFAULT_CHUNKS_DIR) -> List[Document]:
    """
    Load custom chunks from the chunks directory and convert them to Document objects.
    """
    custom_chunks = []
    
    if not os.path.exists(chunks_dir):
        return custom_chunks
    
    chunk_files = [f for f in os.listdir(chunks_dir) if f.endswith('.txt')]
    
    for chunk_file in chunk_files:
        chunk_path = os.path.join(chunks_dir, chunk_file)
        try:
            with open(chunk_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:  # Only add non-empty chunks
                    # Create metadata with source as the chunk filename
                    metadata = {"source": f"custom_chunk_{chunk_file}"}
                    custom_chunks.append(Document(page_content=content, metadata=metadata))
        except Exception as e:
            st.warning(f"⚠️ Failed to load custom chunk {chunk_file}: {e}")
    
    print(f"📁 Loaded {len(custom_chunks)} custom chunks from '{chunks_dir}/'")
    return custom_chunks

def get_vectorstore(
    file_list: List[str],
    docs_dir: str = DEFAULT_DOCS_DIR,
    persist_dir: str = DEFAULT_PERSIST_DIR,
    chunks_dir: str = DEFAULT_CHUNKS_DIR
) -> Chroma:
    """
    Incrementally update a Chroma vectorstore by embedding only new files and custom chunks.
    """
    embedding = OpenAIEmbeddings(
        model="text-embedding-3-large",
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

    # Load previously processed custom chunks list
    custom_chunks_cache_path = os.path.join(persist_dir, "custom_chunks.txt")
    prev_custom_chunks = set()
    if os.path.exists(custom_chunks_cache_path):
        with open(custom_chunks_cache_path, "r", encoding="utf-8") as f:
            prev_custom_chunks = set(line.strip() for line in f)

    # Filter new files
    new_files = [f for f in file_list if f not in prev_files]
    
    # Load custom chunks and filter new ones
    all_custom_chunks = load_custom_chunks(chunks_dir)
    new_custom_chunks = []
    new_custom_chunk_files = []
    
    for chunk in all_custom_chunks:
        chunk_filename = chunk.metadata["source"].replace("custom_chunk_", "")
        if chunk_filename not in prev_custom_chunks:
            new_custom_chunks.append(chunk)
            new_custom_chunk_files.append(chunk_filename)
    
    all_chunks = []
    
    # Process new files if any
    if new_files:
        print(f"🆕 New files to process: {new_files}")
        docs = extract_text(new_files, docs_dir)
        file_chunks = get_text_chunks(docs)
        all_chunks.extend(file_chunks)
    
    # Add new custom chunks
    if new_custom_chunks:
        all_chunks.extend(new_custom_chunks)
        print(f"📁 Added {len(new_custom_chunks)} new custom chunks to processing queue")
    
    if not all_chunks:
        print("✅ No new files or custom chunks to add.")
        return vectordb

    # Deduplicate by chunk content hash
    seen_hashes = set()
    unique_chunks: List[Document] = []
    for chunk in all_chunks:
        content_hash = hash_text(chunk.page_content)
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_chunks.append(chunk)

    # Add only unique chunks
    if unique_chunks:
        vectordb.add_documents(unique_chunks)
        vectordb.persist()
        print(f"✅ Added {len(unique_chunks)} unique chunks to vector database.")
    else:
        print("⚠️ No unique chunks to embed — skipping update.")

    # Append new files to file cache (only for document files, not custom chunks)
    if new_files:
        with open(cache_path, "a", encoding="utf-8") as f:
            for fname in new_files:
                f.write(fname + "\n")

    # Append new custom chunks to custom chunks cache
    if new_custom_chunk_files:
        with open(custom_chunks_cache_path, "a", encoding="utf-8") as f:
            for chunk_filename in new_custom_chunk_files:
                f.write(chunk_filename + "\n")

    # Save new chunks for inspection (only for document files, not custom chunks)
    if new_files:
        save_text_chunks(file_chunks, chunks_dir=chunks_dir, overwrite=False)

    return vectordb

def force_refresh_with_custom_chunks(
    persist_dir: str = DEFAULT_PERSIST_DIR,
    chunks_dir: str = DEFAULT_CHUNKS_DIR
) -> Chroma:
    """
    Force refresh the vector database to include all custom chunks.
    This is useful when you want to ensure all custom chunks are included
    even if there are no new document files.
    """
    embedding = OpenAIEmbeddings(
        model="text-embedding-3-large",
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    # Load or create vectorstore
    vectordb = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding
    )

    # Load custom chunks
    custom_chunks = load_custom_chunks(chunks_dir)
    
    if custom_chunks:
        # Clear the custom chunks cache to force re-processing
        custom_chunks_cache_path = os.path.join(persist_dir, "custom_chunks.txt")
        if os.path.exists(custom_chunks_cache_path):
            os.remove(custom_chunks_cache_path)
        
        # Add custom chunks to vector database
        vectordb.add_documents(custom_chunks)
        vectordb.persist()
        
        # Update the custom chunks cache
        with open(custom_chunks_cache_path, "w", encoding="utf-8") as f:
            for chunk in custom_chunks:
                chunk_filename = chunk.metadata["source"].replace("custom_chunk_", "")
                f.write(chunk_filename + "\n")
        
        print(f"✅ Force refreshed vector database with {len(custom_chunks)} custom chunks.")
    else:
        print("⚠️ No custom chunks found to add.")
    
    return vectordb

def has_new_custom_chunks(persist_dir: str = DEFAULT_PERSIST_DIR, chunks_dir: str = DEFAULT_CHUNKS_DIR) -> bool:
    """
    Check if there are new custom chunks that haven't been processed yet.
    """
    if not os.path.exists(chunks_dir):
        return False
    
    # Get current custom chunk files
    current_chunk_files = set(f for f in os.listdir(chunks_dir) if f.endswith('.txt'))
    
    # Get previously processed custom chunk files
    custom_chunks_cache_path = os.path.join(persist_dir, "custom_chunks.txt")
    prev_custom_chunks = set()
    if os.path.exists(custom_chunks_cache_path):
        with open(custom_chunks_cache_path, "r", encoding="utf-8") as f:
            prev_custom_chunks = set(line.strip() for line in f)
    
    # Check if there are new chunks
    new_chunks = current_chunk_files - prev_custom_chunks
    return len(new_chunks) > 0
