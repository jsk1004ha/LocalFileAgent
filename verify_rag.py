from src.tools.search import DocumentSearcher
import os
import shutil

# Clean up any previous state to test migration or fresh index
# db_path = ".chromadb"
# if os.path.exists(db_path):
#    shutil.rmtree(db_path)

s = DocumentSearcher(r'C:\Users\js100\Desktop') # Just desktop for quick test
print("Running RAG Indexing...")
stats = s.index_documents()
print(f"Stats: {stats}")

# Check chunking
all_docs = s.collection.get()
if all_docs['ids']:
    print(f"First 5 IDs: {all_docs['ids'][:5]}")
    # Verify '#' in IDs
    has_chunks = any('#' in doc_id for doc_id in all_docs['ids'])
    print(f"Has Chunks (# in IDs): {has_chunks}")
else:
    print("No documents found.")
