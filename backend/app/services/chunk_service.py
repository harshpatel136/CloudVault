from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)


def chunk_documents(documents: list[Document]) -> list[Document]:
    return text_splitter.split_documents(documents)
