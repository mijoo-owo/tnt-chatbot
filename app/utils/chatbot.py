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
            # Show user's message immediately
            chat_history = chat_history[-9:] + [HumanMessage(content=user_query)]
            for message in chat_history:
                role = "AI" if isinstance(message, AIMessage) else "Human"
                with st.chat_message(role):
                    st.write(message.content)

            # Prepare streaming LLM chain
            chain = get_context_retriever_chain(vectordb)
            # Create a placeholder for the AI's response
            with st.chat_message("AI"):
                placeholder = st.empty()
                final_response = ""
                # Stream the response token by token (simulate streaming)
                for chunk in chain.stream({"input": user_query, "chat_history": chat_history}):
                    content = ""
                    if isinstance(chunk, dict):
                        content = chunk.get("answer") or chunk.get("result") or ""
                    elif hasattr(chunk, 'text'):
                        content = chunk.text
                    final_response += content
                    placeholder.markdown(final_response + "▌")  # Blinking cursor
                placeholder.markdown(final_response)  # Remove cursor at end

            # Add the AI's response to chat history
            chat_history = chat_history + [AIMessage(content=final_response)]

        except Exception as e:
            st.error(f"❌ Error in chat: {e}")
            # Add error message to chat history
            chat_history = chat_history[-9:] + [
                AIMessage(content="I'm sorry, I encountered an error. Please try again.")
            ]

    else:
        # Display chat messages if no new user input
        for message in chat_history:
            role = "AI" if isinstance(message, AIMessage) else "Human"
            with st.chat_message(role):
                st.write(message.content)

    return chat_history