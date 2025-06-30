import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain.schema import StrOutputParser
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.prompt import prompt_template
from dotenv import load_dotenv
load_dotenv()
os.environ["OPENAI_API_KEY"]=os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o-mini")
prompt_template=prompt_template()
prompt = ChatPromptTemplate.from_template(prompt_template)
class TaxConsultantRAG:
    def __init__(self, pdf_path: str, faiss_index_path: str = "faiss_index"):
        self.pdf_path = pdf_path
        self.faiss_index_path = faiss_index_path
        self.embeddings = OpenAIEmbeddings()
        self.vectorstore = None
        self.retriever = None
        self.chain = None

    def load_pdf(self):
        loader = PyPDFLoader(self.pdf_path)
        documents = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
        docs = text_splitter.split_documents(documents)
        return docs

    def build_vectorstore(self, documents):
        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        self.vectorstore.save_local(self.faiss_index_path)

    def load_vectorstore(self):
        if os.path.exists(self.faiss_index_path):
            self.vectorstore = FAISS.load_local(self.faiss_index_path, self.embeddings)
            self.retriever = self.vectorstore.as_retriever()
        else:
            raise FileNotFoundError("FAISS index not found. Run build_vectorstore() first.")

    def generate_answer(self, query: str):
        if not self.retriever:
            # Ensure retriever is loaded if it wasn't built/loaded previously
            if self.vectorstore is None and os.path.exists(self.faiss_index_path):
                 self.load_vectorstore()
            elif self.vectorstore is not None:
                 self.retriever = self.vectorstore.as_retriever()
            else:
                 raise ValueError("Vectorstore not loaded or built. Cannot create retriever.")

        # Define a function to format the retrieved documents into a single string
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        self.chain = (
            {"context": self.retriever | RunnableLambda(format_docs), "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        return self.chain.invoke(query)
    

if __name__=="__main__":
    app = TaxConsultantRAG(r"C:\Users\Zbook\Desktop\AI_APP\MCP-chainlit\data\tax_calculations.pdf")
    docs = app.load_pdf()
    app.build_vectorstore(docs)
    app.generate_answer("tell me about this document in few sentence")
