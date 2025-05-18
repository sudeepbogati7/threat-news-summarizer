from langchain_community.document_loaders import JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from src.core.config import settings
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

qa_chain = None

def load_and_process_articles(file_path: str = "data/articles.json"):
    global qa_chain
    try:
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

        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        splits = text_splitter.split_documents(documents)

        # Create vector store
        embeddings = OpenAIEmbeddings(api_key=settings.OPENAI_API_KEY)
        vector_store = FAISS.from_documents(splits, embeddings)

        # Set up RAG chain
        llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=settings.OPENAI_API_KEY)
        retriever = vector_store.as_retriever(search_kwargs={"k": 3})
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        logger.info("RAG pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize RAG pipeline: {str(e)}")
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