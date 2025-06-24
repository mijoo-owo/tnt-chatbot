# utils/chatbot.py

import streamlit as st
from collections import defaultdict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from dotenv import load_dotenv

def get_context_retriever_chain(vectordb):
    """
    Create a context retriever chain for generating responses using ChatGPT-4o-mini.
    Simplified version that works reliably.
    """
    load_dotenv()

    # Use OpenAI's GPT-4o-mini via LangChain wrapper
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    # Use standard vector retriever
    retriever = vectordb.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 5}
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful chatbot. You'll receive a prompt that includes a chat history and retrieved content from the vectorDB based on the user's question. Your task is to respond to the user's question using the information from the vectordb, relying as little as possible on your own knowledge. If for some reason you don't know the answer for the question, or the question cannot be answered because there's no context, ask the user for more details. Do not invent an answer, or mention about the knowledge base. Answer the questions from this context: {context}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])

    chain = create_stuff_documents_chain(llm=llm, prompt=prompt)
    retrieval_chain = create_retrieval_chain(retriever, chain)
    return retrieval_chain

def get_response(question, chat_history, vectordb):
    """
    Generate a response using GPT-4o-mini based on the user question and retrieved context.
    Simplified version that works reliably.
    """
    try:
        chain = get_context_retriever_chain(vectordb)
        response = chain.invoke({"input": question, "chat_history": chat_history})
        
        # Fix key access for documents
        return response.get("answer") or response.get("result"), response.get("context") or response.get("source_documents")
    except Exception as e:
        st.error(f"❌ Error generating response: {e}")
        return "I'm sorry, I encountered an error while processing your question. Please try again.", []

def chat(chat_history, vectordb):
    """
    Main Streamlit chat interface using GPT-4o-mini and vector context.
    Simplified version that works reliably.
    """
    user_query = st.chat_input("Ask a question:")
    if user_query:
        try:
            response, context = get_response(user_query, chat_history, vectordb)
            
            # keep the last 9 exchanges + the new one
            chat_history = chat_history[-9:] + [
                HumanMessage(content=user_query),
                AIMessage(content=response)
            ]

            # Show sources in sidebar
            with st.sidebar:
                st.subheader("📚 Sources")
                if context:
                    metadata_dict = defaultdict(list)
                    for doc in context:
                        meta = doc.metadata
                        src = meta.get('source', 'unknown source')
                        pg = meta.get('page')
                        if pg is not None:
                            metadata_dict[src].append(pg)
                    
                    if metadata_dict:
                        for source, pages in metadata_dict.items():
                            st.write(f"**Source:** {source}")
                            if pages:
                                st.write(f"Pages: {', '.join(map(str, pages))}")
                    else:
                        st.write("No page metadata available for these sources.")
                else:
                    st.write("No context found for this answer.")

        except Exception as e:
            st.error(f"❌ Error in chat: {e}")
            # Add error message to chat history
            chat_history = chat_history[-9:] + [
                HumanMessage(content=user_query),
                AIMessage(content="I'm sorry, I encountered an error. Please try again.")
            ]

    # Display chat messages
    for message in chat_history:
        role = "AI" if isinstance(message, AIMessage) else "Human"
        with st.chat_message(role):
            st.write(message.content)

    return chat_history