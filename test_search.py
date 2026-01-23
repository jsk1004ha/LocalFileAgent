from src.tools.search import DocumentSearcher
import os

desktop_path = r'C:\Users\js100\Desktop'
downloads_path = r'C:\Users\js100\Downloads'

print(f"Desktop exists: {os.path.exists(desktop_path)}")
print(f"Downloads exists: {os.path.exists(downloads_path)}")

s = DocumentSearcher(desktop_path, extra_paths=[downloads_path])
print("Indexing documents including Downloads...")
stats = s.index_documents()
print(f"Indexing stats: {stats}")

# Check if specific file is indexed
all_docs = s.collection.get(include=["metadatas"])
print(f"Total indexed documents: {len(all_docs['ids'])}")

# Search for 학급 in filenames
print("\nFiles containing '학급' in filename from all_docs:")
found = False
for i, doc_id in enumerate(all_docs['ids']):
    metadata = all_docs['metadatas'][i]
    if metadata:
        filename = metadata.get('filename', '')
        if '학급' in filename:
            print(f"  - {filename}")
            print(f"    Path: {metadata.get('path', '')}")
            found = True

if not found:
    print("No files with '학급' found in index.")

print("\nExecuting search for '학급세미나 보고서'...")
results = s.search("학급세미나 보고서")
for r in results:
    match_type = getattr(r, 'match_type', 'semantic')
    print(f"- {r['filename']} (Score: {r['score']:.3f}, Type: {match_type})")
    print(f"  Path: {r['path']}")
