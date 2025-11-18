# Deep Dive: Document Processing Pipeline

**Reading time:** 10 minutes
**Commit SHA:** `341e5904c847948d13e339f7df6aacd67ab8b652`

## What You'll Learn

- How RAGFlow's PDF parser achieves "deep document understanding"
- The layout recognition system using ONNX models
- Chunking strategies and when to use each
- The embedding pipeline with batch optimization

---

## Introduction

RAGFlow's headline feature is "deep document understanding"—but what does that actually mean? Unlike simple text extractors that dump PDF content as a string, RAGFlow recognizes document structure: titles, paragraphs, tables, figures, headers, footers, and more.

This post explores the document processing pipeline in detail, from raw PDF bytes to indexed, searchable chunks. We'll look at real code, understand the algorithms, and discuss performance considerations.

---

## The Document Processing Pipeline

```
Raw Document
    │
    ▼
┌─────────────────┐
│ Format Detection │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────┐
│ Content Extract │────▶│ OCR Engine  │
│ (per format)    │     │ (if needed) │
└────────┬────────┘     └──────┬──────┘
         │                     │
         └──────────┬──────────┘
                    │
                    ▼
         ┌──────────────────┐
         │ Layout Recognition│
         │ (11 element types)│
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ Chunking Strategy │
         │ (naive/hier/tree) │
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │ Embedding + Index │
         └──────────────────┘
```

---

## PDF Parser Deep Dive

The PDF parser (`deepdoc/parser/pdf_parser.py`) is the most complex component at 1,400+ lines. Let's understand its approach.

### Initial Extraction

```python
# deepdoc/parser/pdf_parser.py (simplified)
class RAGFlowPdfParser:
    def __call__(self, filename, binary=None, **kwargs):
        # Load PDF
        self.pdf = pdfplumber.open(BytesIO(binary))

        # Extract text and images from each page
        for page_num, page in enumerate(self.pdf.pages):
            # Get text with position info
            chars = page.chars  # Character-level positions
            words = page.extract_words()

            # Get images
            images = page.images

            # Determine if OCR is needed
            if self._needs_ocr(chars, images):
                self._run_ocr(page_num, page.to_image())
```

**Code reference:** [deepdoc/parser/pdf_parser.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/deepdoc/parser/pdf_parser.py)

### Layout Recognition

The magic happens in layout recognition. RAGFlow uses ONNX models to classify document regions into 11 types:

```python
# deepdoc/vision/layout_recognizer.py
LAYOUT_LABELS = [
    "text",          # Body text
    "title",         # Section titles
    "figure",        # Images/charts
    "figure_caption",
    "table",
    "table_caption",
    "header",        # Page headers
    "footer",        # Page footers
    "reference",     # Bibliography
    "equation",      # Math formulas
    "background"     # Watermarks, etc.
]

class LayoutRecognizer(Recognizer):
    def __call__(self, image_list, ocr_results):
        # Run ONNX model inference
        boxes = []
        for img in image_list:
            detections = self.session.run(None, {"images": img})
            for det in detections:
                label_id, confidence, x1, y1, x2, y2 = det
                boxes.append({
                    'type': LAYOUT_LABELS[label_id],
                    'score': confidence,
                    'bbox': [x1, y1, x2, y2]
                })
        return boxes
```

**Code reference:** [deepdoc/vision/layout_recognizer.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/deepdoc/vision/layout_recognizer.py)

### Text Concatenation Intelligence

One clever feature: RAGFlow uses an XGBoost model to decide whether text blocks should be concatenated vertically:

```python
# In pdf_parser.py
def _concat_up_down(self, top_block, bottom_block):
    """Decide if blocks should merge based on features"""
    features = [
        top_block['width'] / page_width,
        bottom_block['width'] / page_width,
        gap_between / top_block['height'],
        same_font,
        same_size,
        # ... more features
    ]
    return self.updown_model.predict([features])[0] == 1
```

This learned model captures patterns like "continuation paragraphs" vs "new sections" better than hand-coded rules.

---

## OCR Engine

When documents are scanned images or contain embedded images, RAGFlow runs OCR:

```python
# deepdoc/vision/ocr.py (simplified)
class OCR(Recognizer):
    def __call__(self, images):
        results = []
        for img in images:
            # Text detection (find text regions)
            boxes = self.text_detector(img)

            # Text recognition (read characters)
            for box in boxes:
                cropped = self._crop(img, box)
                text = self.text_recognizer(cropped)
                results.append({
                    'text': text,
                    'bbox': box,
                    'confidence': score
                })
        return results
```

**Key optimization:** OCR runs with batch processing and GPU acceleration when available:

```python
# GPU memory management
cuda_provider_options = {
    "device_id": 0,
    "gpu_mem_limit": 2048 * 1024 * 1024,  # 2GB
    "arena_extend_strategy": "kNextPowerOfTwo"
}
```

**Code reference:** [deepdoc/vision/ocr.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/deepdoc/vision/ocr.py)

---

## Table Structure Recognition

Tables are particularly challenging. RAGFlow uses a dedicated model to extract table structure:

```python
# deepdoc/vision/table_structure_recognizer.py
class TableStructureRecognizer(Recognizer):
    def __call__(self, table_images):
        """Extract rows and columns from table images"""
        results = []
        for img in table_images:
            # Detect cell boundaries
            cells = self.session.run(None, {"image": img})

            # Convert to row/column structure
            rows = self._cells_to_rows(cells)
            results.append(rows)
        return results
```

The output preserves table semantics for better retrieval—you can search for values and get the full table context.

**Code reference:** [deepdoc/vision/table_structure_recognizer.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/deepdoc/vision/table_structure_recognizer.py)

---

## Chunking Strategies

After parsing, documents are split into chunks for retrieval. RAGFlow offers multiple strategies:

### 1. Naive Merge (Default)

Token-count based splitting with overlap:

```python
# rag/nlp/__init__.py
def naive_merge(sections, chunk_token_num=512, delimiter="\n。；！？"):
    """Simple token-based chunking"""
    chunks = []
    current_chunk = ""
    current_tokens = 0

    for section in sections:
        section_tokens = num_tokens(section['text'])

        if current_tokens + section_tokens > chunk_token_num:
            # Save current chunk
            if current_chunk:
                chunks.append(current_chunk)
            # Start new chunk (with overlap)
            current_chunk = section['text']
            current_tokens = section_tokens
        else:
            current_chunk += delimiter + section['text']
            current_tokens += section_tokens

    return chunks
```

**When to use:** General documents without strong structure.

### 2. Hierarchical Merge

Preserves document structure by detecting bullet patterns:

```python
# rag/nlp/__init__.py
BULLET_PATTERNS = [
    r"第[一二三四五六七八九十百]+[章节条款]",  # Chinese: 第一章
    r"Chapter\s+\d+",                          # Chapter 1
    r"^[IVX]+\.",                              # Roman: I. II. III.
    r"^#{1,6}\s",                              # Markdown: # ## ###
]

def hierarchical_merge(sections, chunk_token_num=512):
    """Structure-preserving chunking"""
    # Build tree from section headers
    tree = build_hierarchy_tree(sections)

    # Merge within hierarchy levels
    chunks = []
    for node in tree.traverse():
        if node.token_count <= chunk_token_num:
            chunks.append(node.content)
        else:
            # Split large nodes
            chunks.extend(split_node(node, chunk_token_num))

    return chunks
```

**When to use:** Well-structured documents (legal, academic, manuals).

**Code reference:** [rag/nlp/__init__.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/nlp/__init__.py)

### 3. Tree Merge

Maintains full document outline hierarchy:

```python
def tree_merge(sections, max_depth=3):
    """Outline-based chunking"""
    tree = build_outline_tree(sections)

    # Collapse beyond max_depth
    for node in tree.traverse():
        if node.depth > max_depth:
            node.parent.content += node.content
            tree.remove(node)

    return [node.content for node in tree.leaves()]
```

**When to use:** Documents with table of contents you want to preserve.

### Choosing the Right Strategy

| Document Type | Recommended Strategy | Chunk Size |
|---------------|---------------------|------------|
| General text | Naive | 512 tokens |
| Legal documents | Hierarchical | 1024 tokens |
| Academic papers | Hierarchical | 512 tokens |
| Books with chapters | Tree | 1024 tokens |
| Q&A documents | QA extraction | N/A |

---

## Embedding Pipeline

After chunking, content is embedded for semantic search:

```python
# rag/flow/tokenizer/tokenizer.py
class Tokenizer:
    def __init__(self, embedding_model, callback=None):
        self.embd_mdl = embedding_model
        self.callback = callback

    async def _embedding(self, chunks):
        """Batch embed chunks with progress reporting"""
        texts = [c['content'] for c in chunks]
        batch_size = 16

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]

            # Run in thread pool for async
            embeddings = await trio.to_thread.run_sync(
                self.embd_mdl.encode, batch
            )
            all_embeddings.extend(embeddings)

            # Report progress
            if self.callback and i % 32 == 0:
                self.callback(0.5 + 0.5 * i / len(texts))

        return all_embeddings
```

**Key optimizations:**

1. **Batch processing**: 16 chunks per API call
2. **Async execution**: Non-blocking with Trio
3. **Progress reporting**: User feedback on long operations

**Code reference:** [rag/flow/tokenizer/tokenizer.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/flow/tokenizer/tokenizer.py)

### Dual Embedding Strategy

RAGFlow embeds both filename and content:

```python
def embed_chunk(chunk, embd_mdl):
    """Embed with filename weighting"""
    # Embed content
    content_vec = embd_mdl.encode([chunk['content']])[0]

    # Embed filename (for relevance boost)
    filename_vec = embd_mdl.encode([chunk['filename']])[0]

    # Weighted combination (configurable)
    weight = 0.1  # filename weight
    final_vec = (1 - weight) * content_vec + weight * filename_vec

    return final_vec
```

This boosts retrieval when queries mention document names.

---

## Indexing

Finally, chunks are indexed in Elasticsearch (or Infinity):

```python
# rag/utils/es_conn.py
class ESConnection:
    def insert(self, chunks, index_name):
        """Bulk insert chunks"""
        actions = []
        for chunk in chunks:
            action = {
                "_index": index_name,
                "_id": chunk['id'],
                "_source": {
                    "content_ltks": chunk['content'],    # Full-text
                    "q_vec": chunk['embedding'],         # Dense vector
                    "docnm_kwd": chunk['filename'],
                    "kb_id": chunk['kb_id'],
                    "doc_id": chunk['doc_id'],
                    "page_num_int": chunk['page_num'],
                    # ... more fields
                }
            }
            actions.append(action)

        # Bulk insert
        helpers.bulk(self.es, actions)
```

**Index schema** supports both full-text and vector search:

```json
{
  "properties": {
    "content_ltks": { "type": "text", "analyzer": "standard" },
    "q_vec": { "type": "dense_vector", "dims": 1024 },
    "docnm_kwd": { "type": "keyword" },
    "kb_id": { "type": "keyword" }
  }
}
```

**Code reference:** [rag/utils/es_conn.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/utils/es_conn.py)

---

## Performance Considerations

### PDF Parsing: The Bottleneck

PDF parsing is CPU-intensive due to:
- Layout recognition model inference
- OCR for scanned documents
- Table structure detection

**Typical times:**
- 10-page text PDF: 5-10 seconds
- 50-page PDF with images: 30-60 seconds
- 100-page scanned PDF: 2-5 minutes

### Optimization Techniques Used

1. **Model caching**: ONNX models loaded once
2. **Parallel page processing**: Multiple pages processed concurrently
3. **GPU acceleration**: CUDA for OCR when available
4. **Capacity limiters**: Prevent memory exhaustion

```python
# Parallel processing with limits
parallel_limiter = trio.CapacityLimiter(4)  # Max 4 concurrent

async with parallel_limiter:
    result = await process_page(page)
```

### Embedding Pipeline

Embedding is often API-bound (external services). Optimizations:
- Batch size of 16 balances latency vs throughput
- Async processing keeps the system responsive
- Token counting prevents exceeding model limits

---

## Specialized Parsers

Beyond general PDFs, RAGFlow includes specialized parsers in `rag/app/`:

| Parser | File | Use Case |
|--------|------|----------|
| QA | `qa.py` | Question-answer documents |
| Table | `table.py` | Data-heavy spreadsheets |
| Laws | `laws.py` | Legal documents (articles, clauses) |
| Paper | `paper.py` | Academic papers (abstract, sections) |
| Resume | `resume.py` | CVs (education, experience, skills) |
| Book | `book.py` | Books with chapters |

Example: The legal parser detects article numbers:

```python
# rag/app/laws.py
ARTICLE_PATTERN = r"第[一二三四五六七八九十百千]+条"

def chunk_legal_document(sections):
    """Chunk by legal article boundaries"""
    chunks = []
    current_article = []

    for section in sections:
        if re.match(ARTICLE_PATTERN, section['text']):
            if current_article:
                chunks.append('\n'.join(current_article))
            current_article = [section['text']]
        else:
            current_article.append(section['text'])

    return chunks
```

**Code reference:** [rag/app/laws.py](https://github.com/infiniflow/ragflow/blob/341e5904c847948d13e339f7df6aacd67ab8b652/rag/app/laws.py)

---

## Key Takeaways

1. **"Deep document understanding" = layout recognition + structural chunking**. RAGFlow uses ONNX models to classify 11 document element types.

2. **The PDF parser is sophisticated** with text concatenation decisions made by a learned XGBoost model.

3. **Chunking strategy matters**. Choose based on document structure: naive for general text, hierarchical for structured documents.

4. **Embedding is optimized for batch processing** with async execution and progress reporting.

5. **Performance is bounded by PDF parsing**, especially for scanned documents requiring OCR.

---

## What's Next

In [Blog 3: Patterns and Practices](./03-patterns-practices.md), we'll explore the design patterns used throughout RAGFlow—factory patterns for LLMs, service layer inheritance, and error handling strategies.

---

## Further Reading

- [Metrics Summary](../initial-analysis/metrics-summary.md) - Performance benchmarks
- [RFC-0002: PDF Parser Modularization](../rfcs/RFC-0002-pdf-parser-modularization.md)
- [Terminology Glossary](../initial-analysis/terminology-glossary.md)
