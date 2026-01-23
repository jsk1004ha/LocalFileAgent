"""
Document Search Tool - Semantic search using ChromaDB and Sentence-Transformers
Optimized with: Multiprocessing, Producer-Consumer pattern, PyMuPDF, mtime tracking, batch embedding
Restricted to: Documents Only (PDF, DOCX, PPTX, HWP, TXT, MD)
"""
import os
import json
import time
import multiprocessing
from pathlib import Path
from typing import Optional, Callable, List, Tuple
from concurrent.futures import ProcessPoolExecutor, as_completed

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import zipfile
import xml.etree.ElementTree as ET
import zlib
import struct

# Optional Libraries for Document Parsing
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None

try:
    from pptx import Presentation
except ImportError:
    Presentation = None

try:
    import olefile
except ImportError:
    olefile = None

# TARGET EXTENSIONS: Purely Text & Documents
CONTENT_EXTENSIONS = {
    # Text
    '.txt', '.md', '.markdown', '.rst', '.log',
    # Office
    '.doc', '.docx', '.hwp', '.hwpx', '.ppt', '.pptx', '.xls', '.xlsx', '.odt', '.csv',
    # PDF
    '.pdf',
}

# No Name-Only for now (User requested "Just documents")

# Batch size for embedding generation
EMBEDDING_BATCH_SIZE = 64

class SimpleTextSplitter:
    """Simple recursive character text splitter."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", " ", ""]
        
    def split_text(self, text: str) -> list[str]:
        """Split text into chunks."""
        final_chunks = []
        remaining_text = text
        
        while remaining_text:
            if len(remaining_text) <= self.chunk_size:
                final_chunks.append(remaining_text)
                break
            
            split_idx = -1
            best_sep = ""
            for sep in self.separators:
                limit = self.chunk_size
                possible_split = remaining_text.rfind(sep, 0, limit)
                if possible_split != -1:
                    split_idx = possible_split
                    best_sep = sep
                    break
            
            if split_idx == -1:
                split_idx = self.chunk_size
                best_sep = ""
            
            chunk = remaining_text[:split_idx]
            final_chunks.append(chunk)
            remaining_text = remaining_text[split_idx + len(best_sep):]
            
        return final_chunks

# Worker function
def process_single_file_worker(args):
    """
    Worker process: Reads file config, extracts content, chunks text.
    """
    file_path, mtime, content_exts, splitter_config = args
    str_path = str(file_path)
    file_path_obj = Path(file_path)
    ext = file_path_obj.suffix.lower()
    
    splitter = SimpleTextSplitter(**splitter_config)
    content = None
    
    try:
        # 1. PDF
        if ext == '.pdf':
            text = ""
            if fitz:
                with fitz.open(file_path) as doc:
                    for page in doc: text += page.get_text() + "\n"
            elif pypdf:
                with open(file_path, 'rb') as f:
                    reader = pypdf.PdfReader(f)
                    for page in reader.pages:
                        x = page.extract_text()
                        if x: text += x + "\n"
            else:
                text = None # No parser
            content = text
            
        # 2. DOCX
        elif ext == '.docx':
            if DocxDocument:
                doc = DocxDocument(file_path)
                content = "\n".join([p.text for p in doc.paragraphs])
            else:
                content = None
                
        # 3. PPTX
        elif ext == '.pptx':
            if Presentation:
                prs = Presentation(file_path)
                text = []
                for slide in prs.slides:
                    for shape in slide.shapes:
                        if hasattr(shape, "text"):
                            text.append(shape.text)
                content = "\n".join(text)
            else:
                content = None

        # 4. HWP (Legacy & HWP 5.0)
        elif ext == '.hwp':
            if olefile and olefile.isOleFile(file_path):
                try:
                    f = olefile.OleFileIO(file_path)
                    dirs = f.listdir()
                    
                    # HWP 5.0+ BodyText extraction
                    # BodyText/SectionX streams contain zlib compressed text
                    body_text = ""
                    valid_sections = [d for d in dirs if d[0] == "BodyText"]
                    
                    # Sort by section number if possible, though dirs might be unordered
                    # Usually Section0, Section1...
                    
                    for section in valid_sections:
                        try:
                            stream = f.openstream(section)
                            data = stream.read()
                            # Decompress (raw deflate usually, sometimes with header)
                            # HWP uses raw deflate (w/o header) often, logic is complex.
                            # Simplified Attempt: Try decompress with -15 (raw)
                            try:
                                decompressed = zlib.decompress(data, -15)
                            except:
                                try:
                                    decompressed = zlib.decompress(data)
                                except:
                                    decompressed = None
                            
                            if decompressed:
                                # HWP text is UTF-16LE
                                body_text += decompressed.decode('utf-16le', errors='ignore') + "\n"
                        except:
                            pass
                    
                    # If BodyText found, use it.
                    if body_text.strip():
                        # Basic cleanup: remove control characters roughly
                        import re
                        # HWP control chars are mixed, this is a rough filter for readable text
                        clean_text = re.sub(r'[\x00-\x09\x0b\x0c\x0e-\x1f]', '', body_text)
                        content = clean_text
                    
                    # Fallback for older HWP or if extraction failed
                    if not content:
                        # Try PrvText if available (preview text)
                        if ["PrvText"] in dirs:
                            stream = f.openstream("PrvText")
                            # PrvText is usually UTF-16LE
                            content = stream.read().decode('utf-16le', errors='ignore')
                            
                except Exception as e:
                    # Generic failure, content remains None
                    pass
                finally:
                    if 'f' in locals(): f.close()

        # 4.5 HWPX (Zip + XML)
        elif ext == '.hwpx':
            try:
                with zipfile.ZipFile(file_path, 'r') as zf:
                    # Main content is properly in Contents/section0.xml
                    # But finding all sections is safer.
                    # Structure: Contents/*.xml
                    text_parts = []
                    for name in zf.namelist():
                        if name.startswith('Contents/section') and name.endswith('.xml'):
                            with zf.open(name) as xml_file:
                                tree = ET.parse(xml_file)
                                root = tree.getroot()
                                # Extract all text from xml tags
                                # Use iter method
                                for elem in root.iter():
                                    if elem.text:
                                        text_parts.append(elem.text.strip())
                    content = "\n".join(t for t in text_parts if t)
            except:
                content = None
        
        # 5. Text / MD / Code (if included)
        elif ext in ['.txt', '.md', '.markdown', '.rst', '.log', '.json', '.xml', '.py', '.js']: 
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
        else:
            # Try generic text read
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
    except (UnicodeDecodeError):
        try:
            with open(file_path, 'r', encoding='cp949') as f:
                content = f.read()
        except:
            content = None
    except Exception:
        content = None
        
    # Validation
    if content is None:
        # Fallback to Filename for Documents where content read failed (e.g. HWP without parser)
        # User requested "Document Files only". Even if we can't read content, indexing Filename is better than nothing for "Search".
        # But for 'private-gpt' style, content is key.
        content = f"Filename: {file_path_obj.name}\nPath: {str_path}\n(Content extraction failed or parser missing)"
    
    chunks = splitter.split_text(content)
    if not chunks:
        chunks = [content[:1000]]
        
    return (str_path, chunks, mtime, file_path_obj.name, ext)


class DocumentSearcher:
    
    def __init__(self, base_path: str, db_path: str = ".chromadb", extra_paths: list = None):
        self.base_path = Path(base_path)
        self.extra_paths = [Path(p) for p in (extra_paths or [])]
        self.all_paths = [self.base_path] + self.extra_paths
        self.db_path = Path(base_path) / db_path
        self.model_name = "distiluse-base-multilingual-cased-v2"
        self._model: Optional[SentenceTransformer] = None
        
        self.splitter_config = {"chunk_size": 1000, "chunk_overlap": 200}
        self.state_path = self.db_path.parent / "index_state.json"
        
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}
        )
        
    def add_path(self, path: Path):
        """Add a new path to the index list."""
        if path not in self.all_paths:
            self.all_paths.append(path)
            if path not in self.extra_paths:
                self.extra_paths.append(path)
        
    def is_indexed(self) -> bool:
        """Check if any documents are indexed."""
        return self.collection.count() > 0

    def clear_index(self):
        """Clear all indexed documents."""
        try:
            self.client.delete_collection("documents")
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            if self.state_path.exists():
                os.remove(self.state_path)
            return True
        except Exception as e:
            print(f"Index clear failed: {e}")
            return False

        
    def _load_state(self) -> dict:
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_state(self, state: dict):
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except:
            pass

    def _get_file_mtime(self, file_path: Path) -> float:
        try:
            return file_path.stat().st_mtime
        except:
            return 0.0
    
    def index_documents(self, force_reindex: bool = False, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> dict:
        """
        Index Documents Only.
        """
        if not force_reindex:
            if not self.state_path.exists() and self.collection.count() > 0:
                force_reindex = True

        if force_reindex:
            self.client.delete_collection("documents")
            self.collection = self.client.get_or_create_collection(
                name="documents",
                metadata={"hnsw:space": "cosine"}
            )
            index_state = {}
        else:
            index_state = self._load_state()
        
        files_to_process = []
        current_paths = set()
        
        skip_dirs = {"AppData", "$Recycle.Bin", "ProgramData", "Windows", "System Volume Information", "venv", "node_modules", "__pycache__", ".git", ".venv", ".idea", ".vscode"}
        
        # 1. Faster Scan
        for search_path in self.all_paths:
            if not search_path.exists(): continue
            for root, dirs, files in os.walk(search_path, topdown=True, onerror=lambda e: None):
                dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
                for name in files:
                    file_path = Path(root) / name
                    if any(part.startswith('.') for part in file_path.parts): continue
                    
                    ext = file_path.suffix.lower()
                    
                    # STRICT WHITELIST
                    if ext not in CONTENT_EXTENSIONS:
                        continue
                    
                    str_path = str(file_path)
                    if str_path in current_paths: continue
                    current_paths.add(str_path)
                    
                    mtime = self._get_file_mtime(file_path)
                    if str_path in index_state and not force_reindex:
                        if mtime <= index_state[str_path]:
                            continue
                    
                    files_to_process.append((str_path, mtime))
        
        # 2. Cleanup Orphans
        orphans = set(index_state.keys()) - current_paths
        for p in orphans:
            self.collection.delete(where={"path": p})
            del index_state[p]
            
        total_files = len(files_to_process)
        if total_files == 0:
            self._save_state(index_state)
            return {"indexed": 0, "skipped": len(current_paths), "updated": 0, "deleted": len(orphans), "errors": 0, "total_in_db": self.collection.count()}

        # 3. Multiprocessing Pipeline
        worker_args = []
        for fpath, fmtime in files_to_process:
            worker_args.append((fpath, fmtime, CONTENT_EXTENSIONS, self.splitter_config))
            
        indexed_count = 0
        updated_count = 0
        errors = 0
        
        batch_contents = []
        batch_ids = []
        batch_metas = []
        
        num_workers = max(1, multiprocessing.cpu_count() - 1) 
        
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_file = {executor.submit(process_single_file_worker, arg): arg[0] for arg in worker_args}
            
            processed_so_far = 0
            
            for future in as_completed(future_to_file):
                processed_so_far += 1
                try:
                    str_path, chunks, mtime, fname, ext = future.result()
                    
                    if progress_callback:
                        progress_callback(processed_so_far, total_files, fname)
                    
                    self.collection.delete(where={"path": str_path})
                    
                    for i, txt in enumerate(chunks):
                        batch_contents.append(txt)
                        batch_ids.append(f"{str_path}#{i}")
                        batch_metas.append({
                            "path": str_path,
                            "filename": fname,
                            "extension": ext,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "mtime": mtime
                        })
                        
                        if len(batch_contents) >= EMBEDDING_BATCH_SIZE:
                            self._process_batch(batch_contents, batch_ids, batch_metas)
                            batch_contents, batch_ids, batch_metas = [], [], []
                            
                    index_state[str_path] = mtime
                    if str_path in index_state: updated_count += 1
                    else: indexed_count += 1
                    
                except Exception as e:
                    errors += 1
                    
            if batch_contents:
                self._process_batch(batch_contents, batch_ids, batch_metas)

        self._save_state(index_state)
        
        return {
            "indexed": indexed_count,
            "skipped": len(current_paths) - total_files, 
            "updated": updated_count,
            "deleted": len(orphans),
            "errors": errors,
            "total_in_db": self.collection.count()
        }
    
    def _process_batch(self, contents: list, doc_ids: list, metadatas: list):
        if not contents: return
        embeddings = self._get_model().encode(contents, show_progress_bar=False).tolist()
        self.collection.upsert(ids=doc_ids, embeddings=embeddings, documents=contents, metadatas=metadatas)
    
    def search(self, query: str, top_k: int = 15) -> list[dict]:
        if self.collection.count() == 0: return []
        
        all_docs = self.collection.get(include=["metadatas"])
        filename_matches = []
        query_words = query.lower().split()
        
        for i, meta in enumerate(all_docs['metadatas']):
            if not meta: continue
            fname = meta.get('filename', '').lower()
            score = 0
            for w in query_words:
                if len(w)>=2 and w in fname: score += 1
            if score > 0:
                filename_matches.append({
                    "path": meta.get('path'),
                    "filename": meta.get('filename'),
                    "content_preview": f"Filename Match: {meta.get('filename')}",
                    "score": 0.95 + (score * 0.01),
                    "match_type": "filename"
                })
        
        filename_matches.sort(key=lambda x: x['score'], reverse=True)
        
        q_emb = self._get_model().encode(query).tolist()
        res = self.collection.query(query_embeddings=[q_emb], n_results=min(top_k*2, self.collection.count()))
        
        sem_matches = []
        if res['ids']:
            for i in range(len(res['ids'][0])):
                sem_matches.append({
                    "path": res['metadatas'][0][i]['path'],
                    "filename": res['metadatas'][0][i]['filename'],
                    "content_preview": res['documents'][0][i][:200] + "...",
                    "score": 1 - res['distances'][0][i] if res['distances'] else 0,
                    "match_type": "semantic"
                })
        
        seen = set()
        final = []
        for m in filename_matches[:top_k]:
            if m['path'] not in seen:
                seen.add(m['path'])
                final.append(m)
        for m in sem_matches:
            if len(final) >= top_k: break
            if m['path'] not in seen:
                seen.add(m['path'])
                final.append(m)
                
        return final

    def _get_model(self) -> SentenceTransformer:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)
        return self._model


# LangChain Tool wrapper
def create_search_tool(base_path: str):
    from langchain.tools import tool
    searcher = DocumentSearcher(base_path)
    
    @tool
    def search_docs(query: str) -> str:
        """Search documents by content."""
        results = searcher.search(query)
        if not results: return "No results found."
        out = f"Search Results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            out += f"{i}. {r['filename']}\n   Path: {r['path']}\n   Preview: {r['content_preview']}\n\n"
        return out
    
    @tool
    def index_documents() -> str:
        """Index documents."""
        stats = searcher.index_documents()
        return f"Indexing Complete: {stats}"
    
    return search_docs, index_documents, searcher

if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    s = DocumentSearcher(base)
    print(s.index_documents(progress_callback=lambda c, t, f: print(f"{c}/{t} {f}")))
# LangChain Tool wrapper
def create_search_tool(base_path: str):
    from langchain.tools import tool
    searcher = DocumentSearcher(base_path)
    
    @tool
    def search_docs(query: str) -> str:
        """Search documents by content."""
        results = searcher.search(query)
        if not results: return "No results found."
        out = f"Search Results for '{query}':\n\n"
        for i, r in enumerate(results, 1):
            out += f"{i}. {r['filename']}\n   Path: {r['path']}\n   Preview: {r['content_preview']}\n\n"
        return out
    
    @tool
    def index_documents() -> str:
        """Index documents."""
        stats = searcher.index_documents()
        return f"Indexing Complete: {stats}"
    
    return search_docs, index_documents, searcher

if __name__ == "__main__":
    import sys
    base = sys.argv[1] if len(sys.argv) > 1 else "."
    s = DocumentSearcher(base)
    print(s.index_documents(progress_callback=lambda c, t, f: print(f"{c}/{t} {f}")))
