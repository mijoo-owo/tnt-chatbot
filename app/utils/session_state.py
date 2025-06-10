import os
from utils.prepare_vectordb import get_vectorstore

def initialize_session_state_variables(st):
    if 'processed_documents' not in st.session_state:
        st.session_state.processed_documents = []
    if 'uploaded_pdfs' not in st.session_state:
        st.session_state.uploaded_pdfs = []
    if 'uploaded_urls' not in st.session_state:
        st.session_state.uploaded_urls = []
    if 'vectordb' not in st.session_state:
        st.session_state.vectordb = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'previous_upload_docs_length' not in st.session_state:
        st.session_state.previous_upload_docs_length = 0
