import glob
import os
from concurrent.futures.thread import ThreadPoolExecutor

import langchain_chroma
from langchain_community.document_loaders import DirectoryLoader, PyMuPDFLoader, CSVLoader, UnstructuredXMLLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from tqdm import tqdm


def add_metadata(doc, doc_type):
    doc.metadata["doc_type"] = doc_type
    return doc

def load_documents_by_type(folder, file_type, loaders):
    loader = DirectoryLoader(folder, glob=f"**/*{file_type}", loader_cls=loaders[file_type])
    documents = loader.load()
    #print("The following documents were loaded:")
    #for doc in documents:
    #    print(f" - {doc.metadata.get('source', 'Unknown source')}")
    doc_type = os.path.basename(folder)
    return [add_metadata(doc, doc_type) for doc in documents]

def load_knowledge_base(folders, loaders):
    documents = []
    for folder in folders:
        documents.extend(load_documents_by_type(folder, ".pdf", loaders))
        documents.extend(load_documents_by_type(folder, ".csv", loaders))

    return documents

def split_documents(documents, chunk_size=1000, chunk_overlap=200):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = text_splitter.split_documents(documents)

    print(f"Total number of chunks: {len(chunks)}")
    print(f"Document types found: {set(doc.metadata['doc_type'] for doc in documents)}")
    return chunks

def get_embedding_function(embedding_type="hugging_face", embedding_model="BAAI/bge-small-en-v1.5"):
    if embedding_type == "hugging_face":
        embedding_function = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={"device": "cuda"},  # or "cpu"
            encode_kwargs={"normalize_embeddings": True}
        )
    return embedding_function

def embed_batch(batch, embedding_function):
    texts = [doc.page_content for doc in batch]
    return embedding_function.embed_documents(texts)

def create_embeddings(batch_size=512):
    chunks = split_documents(load_knowledge_base(
        folders = glob.glob("../knowledge/*"),
        loaders={
            ".pdf": DirectoryLoader,
            ".csv": DirectoryLoader
        }
    ))
    # Split docs into batches
    batches = [chunks[i:i + batch_size] for i in range(0, len(chunks), batch_size)]

    all_embeddings = []
    docs = []

    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(embed_batch, batch) for batch in batches]
        for future, batch in tqdm(zip(futures, batches), total=len(batches)):
            embeddings = future.result()
            all_embeddings.extend(embeddings)
            docs.extend(batch)
    return docs


def create_vectorstore(db_name, knowledge_dir="../../knowledge", force=False):
    chunks = split_documents(load_knowledge_base(
        folders=glob.glob(f"{knowledge_dir}/*"),
        loaders={
            '.pdf': PyMuPDFLoader,
            '.xml': UnstructuredXMLLoader,
            '.csv': CSVLoader,
        }
    ))
    # Delete if already exists
    exists = False
    if os.path.exists(db_name):
        exists = True
        if force:
            print(f"Deleting existing vectorstore at {db_name}")
            from langchain_community.vectorstores import Chroma
            Chroma(persist_directory=db_name).delete_collection()
            exists = False

    if exists:
        print(f"Vectorstore already exists at {db_name}. Use force=True to delete it.")
        db = langchain_chroma.Chroma(
            embedding_function=get_embedding_function(),
            persist_directory=db_name
        )
    else:
        print(f"Creating new vectorstore at {db_name}")
        # Now create the vectorstore with precomputed embeddings
        db = langchain_chroma.Chroma.from_documents(
            documents=chunks,
            embedding=get_embedding_function(),
            persist_directory=db_name
        )


    print(f"Vectorstore at {db_name} with {db._collection.count()} documents")
    return db

if __name__ == "__main__":
    # Create the vectorstore
    db_name = "../diet_vector_db"
    db = create_vectorstore(db_name, force=False)
    db.as_retriever()
    # If you want to create embeddings separately
    # docs = create_embeddings(batch_size=512)
    # print(f"Created {len(docs)} documents with embeddings.")