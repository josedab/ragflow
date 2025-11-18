# RFC-0002: PDF Parser Modularization

**Status:** Draft
**Author:** Analysis Team
**Created:** November 18, 2025
**Effort:** 3-4 weeks
**Priority:** P1 (Strategic)

## Summary

Refactor the monolithic PDF parser (1,400+ lines) into smaller, testable modules to improve maintainability, enable parallel processing, and reduce memory usage.

## Motivation

The current PDF parser has several issues:

1. **Monolithic design**: Single file with 1,400+ lines
2. **Hard to test**: Tightly coupled components
3. **Sequential processing**: Pages processed one at a time
4. **Memory inefficient**: Loads entire PDF in memory
5. **Limited extensibility**: Adding new features is risky

Performance impact is significant—PDF parsing is the primary bottleneck for document ingestion.

## Detailed Design

### Module Structure

```
deepdoc/parser/
├── pdf/
│   ├── __init__.py           # Public API
│   ├── loader.py             # PDF loading and page iteration
│   ├── text_extractor.py     # Text extraction with positions
│   ├── layout_analyzer.py    # Layout recognition
│   ├── table_extractor.py    # Table detection and parsing
│   ├── image_extractor.py    # Image extraction
│   ├── ocr_handler.py        # OCR coordination
│   ├── text_merger.py        # Text block merging
│   └── models.py             # Data classes
```

### Core Interfaces

```python
# deepdoc/parser/pdf/models.py
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

@dataclass
class TextBlock:
    text: str
    bbox: BoundingBox
    font: str
    size: float
    page_num: int

@dataclass
class LayoutElement:
    type: str  # text, title, table, figure, etc.
    bbox: BoundingBox
    confidence: float
    content: any

@dataclass
class PageResult:
    page_num: int
    text_blocks: List[TextBlock]
    layout_elements: List[LayoutElement]
    tables: List[dict]
    images: List[bytes]
```

### Module Implementations

```python
# deepdoc/parser/pdf/loader.py
class PDFLoader:
    """Load PDF and iterate pages with lazy loading"""

    def __init__(self, binary: bytes):
        self.pdf = pdfplumber.open(BytesIO(binary))

    def __iter__(self):
        for i, page in enumerate(self.pdf.pages):
            yield i, page

    def get_page(self, page_num: int):
        return self.pdf.pages[page_num]

    @property
    def page_count(self):
        return len(self.pdf.pages)


# deepdoc/parser/pdf/text_extractor.py
class TextExtractor:
    """Extract text with position information"""

    def extract(self, page) -> List[TextBlock]:
        blocks = []
        for char in page.chars:
            blocks.append(TextBlock(
                text=char['text'],
                bbox=BoundingBox(char['x0'], char['top'], char['x1'], char['bottom']),
                font=char.get('fontname', ''),
                size=char.get('size', 0),
                page_num=page.page_number
            ))
        return self._merge_chars_to_blocks(blocks)


# deepdoc/parser/pdf/layout_analyzer.py
class LayoutAnalyzer:
    """Analyze page layout using ONNX model"""

    def __init__(self, model_path: str = None):
        self.model = self._load_model(model_path)

    def analyze(self, page_image) -> List[LayoutElement]:
        detections = self.model.run(page_image)
        return [
            LayoutElement(
                type=LAYOUT_LABELS[det.label_id],
                bbox=BoundingBox(*det.bbox),
                confidence=det.confidence,
                content=None
            )
            for det in detections
        ]


# deepdoc/parser/pdf/text_merger.py
class TextMerger:
    """Merge text blocks using learned model"""

    def __init__(self, model_path: str = None):
        self.model = self._load_xgboost_model(model_path)

    def merge(self, blocks: List[TextBlock], page_size) -> List[TextBlock]:
        merged = []
        for i, block in enumerate(blocks):
            if i > 0 and self._should_merge(blocks[i-1], block, page_size):
                merged[-1] = self._merge_blocks(merged[-1], block)
            else:
                merged.append(block)
        return merged
```

### Parallel Processing

```python
# deepdoc/parser/pdf/__init__.py
import trio

class PDFParser:
    """Main PDF parser with parallel processing"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.loader = PDFLoader
        self.text_extractor = TextExtractor()
        self.layout_analyzer = LayoutAnalyzer()
        self.table_extractor = TableExtractor()
        self.text_merger = TextMerger()
        self.ocr_handler = OCRHandler()

    async def parse(self, binary: bytes, callback=None) -> List[PageResult]:
        """Parse PDF with parallel page processing"""
        loader = self.loader(binary)
        results = [None] * loader.page_count

        # Process pages in parallel
        async with trio.open_nursery() as nursery:
            limiter = trio.CapacityLimiter(4)  # Max 4 concurrent pages

            for page_num, page in loader:
                nursery.start_soon(
                    self._process_page,
                    page_num, page, results, limiter, callback
                )

        return results

    async def _process_page(self, page_num, page, results, limiter, callback):
        """Process single page"""
        async with limiter:
            # Extract text
            text_blocks = self.text_extractor.extract(page)

            # Analyze layout
            page_image = page.to_image()
            layout = self.layout_analyzer.analyze(page_image)

            # OCR if needed
            if self._needs_ocr(text_blocks, layout):
                ocr_blocks = await trio.to_thread.run_sync(
                    self.ocr_handler.process, page_image
                )
                text_blocks.extend(ocr_blocks)

            # Extract tables
            tables = self.table_extractor.extract(page, layout)

            # Merge text
            merged = self.text_merger.merge(text_blocks, page.bbox)

            results[page_num] = PageResult(
                page_num=page_num,
                text_blocks=merged,
                layout_elements=layout,
                tables=tables,
                images=[]
            )

            if callback:
                callback(page_num / len(results))

    def parse_sync(self, binary: bytes, callback=None) -> List[PageResult]:
        """Synchronous wrapper"""
        return trio.run(self.parse, binary, callback)
```

## Example Usage

### Before

```python
from deepdoc.parser.pdf_parser import RAGFlowPdfParser

parser = RAGFlowPdfParser()
sections = parser(filename, binary)  # Returns flat list
```

### After

```python
from deepdoc.parser.pdf import PDFParser

parser = PDFParser()

# Async usage (preferred)
results = await parser.parse(binary, callback=progress_callback)

# Sync usage
results = parser.parse_sync(binary)

# Access structured results
for page_result in results:
    for element in page_result.layout_elements:
        if element.type == "table":
            process_table(element)
        elif element.type == "title":
            process_title(element)
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. Create data models and interfaces
2. Extract `PDFLoader` module
3. Extract `TextExtractor` module
4. Add unit tests for each module

### Phase 2: Core Modules (Week 2)
1. Extract `LayoutAnalyzer` module
2. Extract `TableExtractor` module
3. Extract `TextMerger` module
4. Extract `OCRHandler` module

### Phase 3: Integration (Week 3)
1. Create main `PDFParser` class
2. Implement parallel processing
3. Add async support with Trio
4. Integration tests

### Phase 4: Migration (Week 4)
1. Update `rag/app/naive.py` to use new parser
2. Performance benchmarking
3. Rollback capability
4. Documentation

## Backwards Compatibility

**Breaking changes:**
- Return type changes from flat list to structured `PageResult`
- Async API is now primary

**Migration path:**
```python
# Compatibility wrapper
class LegacyPDFParser:
    def __init__(self):
        self.new_parser = PDFParser()

    def __call__(self, filename, binary):
        results = self.new_parser.parse_sync(binary)
        return self._convert_to_legacy_format(results)
```

## Alternatives Considered

### 1. Keep Monolithic Parser
- **Pros:** No migration risk
- **Cons:** Maintainability degrades over time

### 2. Use External Library (e.g., Docling)
- **Pros:** Less maintenance
- **Cons:** Less control, potential quality issues

### 3. Complete Rewrite
- **Pros:** Clean slate
- **Cons:** High risk, loses institutional knowledge

## Success Criteria

- [ ] PDF parsing time reduced by 30%+ (parallel processing)
- [ ] Memory usage reduced by 20%+ (lazy loading)
- [ ] 90%+ unit test coverage for parser modules
- [ ] No accuracy regression (same outputs for test documents)
- [ ] Documentation for each module

## Rollback Strategy

1. Keep old parser available as `pdf_parser_legacy.py`
2. Feature flag to switch between old/new
3. A/B testing on subset of documents
4. Monitor accuracy metrics before full rollout

## Open Questions

1. Should we support streaming page results?
2. How to handle encrypted PDFs?
3. Should table extraction be optional (for speed)?

## Stakeholder Approvals

- [ ] RAG Team Lead
- [ ] Performance Engineer
- [ ] QA Sign-off
- [ ] Documentation Team
