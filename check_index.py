from src.tools.search import DocumentSearcher

s = DocumentSearcher(r'C:\Users\js100\Desktop', extra_paths=[r'C:\Users\js100\Downloads'])
all_docs = s.collection.get(include=["metadatas"])
downloads_count = 0
for m in all_docs['metadatas']:
    if m and 'Downloads' in str(m.get('path', '')):
        downloads_count += 1
print(f"Total indexed: {len(all_docs['ids'])}")
print(f"Downloads files indexed: {downloads_count}")
