from langchain_community.document_loaders import JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings, HuggingFaceEndpoint
from langchain.chains import RetrievalQA
from src.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

qa_chain = None

# Custom RetrievalQA to allow arbitrary types for callback handlers
class CustomRetrievalQA(RetrievalQA):
    class Config:
        arbitrary_types_allowed = True

def load_and_process_articles(file_path: str = "data/articles.json"):
    global qa_chain
    try:
        logger.info(f"Attempting to load articles from {file_path}")
        if not os.path.exists(file_path):
            logger.error(f"Articles file not found: {file_path}")
            raise FileNotFoundError(f"Articles file not found: {file_path}")

        # Load JSON articles with specific fields
        loader = JSONLoader(
            file_path=file_path,
            jq_schema=".[]",
            text_content=False,
            content_key="content",
            metadata_func=lambda record, metadata: {
                "title": record.get("title", ""),
                "source": record.get("source", {}).get("name", ""),
                "url": record.get("url", ""),
                "published_at": record.get("publishedAt", "")
            }
        )
        documents = loader.load()
        logger.info(f"Loaded {len(documents)} documents from {file_path}")

        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)
        logger.info(f"Split documents into {len(splits)} chunks")

        # Create vector store with Hugging Face Inference API
        if not settings.HUGGINGFACE_API_TOKEN:
            logger.error("HUGGINGFACE_API_TOKEN is not set in environment")
            raise ValueError("HUGGINGFACE_API_TOKEN is not set")

        embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN
        )
        vector_store = FAISS.from_documents(splits, embeddings)
        logger.info("Vector store created successfully with all-MiniLM-L6-v2 via Inference API")

        # Set up RAG chain with Hugging Face Inference API
        llm = HuggingFaceEndpoint(
            repo_id="mistralai/Mixtral-8x7B-Instruct-v0.1",
            huggingfacehub_api_token=settings.HUGGINGFACE_API_TOKEN,
            max_new_tokens=512,
            temperature=0.7
        )
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        qa_chain = CustomRetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        logger.info("RAG pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
        qa_chain = None
        raise

def get_qa_chain():
    return qa_chain

def query_rag(qa_chain, query: str):
    try:
        result = qa_chain({"query": query})
        answer = result["result"]
        sources = [doc.metadata.get("url", "") for doc in result["source_documents"]]
        return {"answer": answer, "sources": sources}
    except Exception as e:
        logger.error(f"Error processing RAG query: {str(e)}")
        raise