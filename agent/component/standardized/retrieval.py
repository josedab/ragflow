#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Standardized Retrieval component using the RFC-0004 interface.

This component demonstrates how to implement a component using the
new standardized interface with Pydantic schemas.
"""

import json
import logging
import re
from functools import partial
from typing import List, Optional, Dict, Any

from pydantic import Field

from agent.component.base import (
    StandardizedComponentBase,
    ComponentInput,
    ComponentOutput,
    ComponentConfig,
)
from api.db.services.dialog_service import meta_filter
from api.db.services.document_service import DocumentService
from api.db.services.knowledgebase_service import KnowledgebaseService
from api.db.services.llm_service import LLMBundle
from common import settings
from common.constants import LLMType
from rag.app.tag import label_question
from rag.prompts.generator import cross_languages, kb_prompt, gen_meta_filter


class RetrievalInput(ComponentInput):
    """Input schema for Retrieval component."""

    query: str = Field(..., description="Search query", min_length=0)
    top_k: int = Field(default=5, description="Number of results to return", ge=1, le=100)


class RetrievalOutput(ComponentOutput):
    """Output schema for Retrieval component."""

    chunks: List[dict] = Field(default_factory=list, description="Retrieved chunks")
    total: int = Field(default=0, description="Total number of results")
    references: List[str] = Field(default_factory=list, description="Reference document names")
    formalized_content: str = Field(default="", description="Formatted content for LLM")
    json_output: List[dict] = Field(default_factory=list, description="Raw JSON output")


class MetaDataFilterConfig(ComponentConfig):
    """Configuration for metadata filtering."""

    method: Optional[str] = Field(default=None, description="Filter method: 'auto' or 'manual'")
    manual: List[dict] = Field(default_factory=list, description="Manual filter conditions")


class RetrievalConfig(ComponentConfig):
    """Configuration schema for Retrieval component."""

    kb_ids: List[str] = Field(default_factory=list, description="Knowledge base IDs")
    kb_vars: List[str] = Field(default_factory=list, description="Knowledge base variable references")
    similarity_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Minimum similarity threshold"
    )
    keywords_similarity_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for keyword similarity"
    )
    top_n: int = Field(default=8, ge=1, description="Number of top results")
    top_k: int = Field(default=1024, ge=1, description="Number of candidates for reranking")
    rerank_id: str = Field(default="", description="Reranker model ID")
    empty_response: str = Field(default="", description="Response when no results found")
    use_kg: bool = Field(default=False, description="Use knowledge graph")
    cross_languages: List[str] = Field(default_factory=list, description="Cross-language search languages")
    toc_enhance: bool = Field(default=False, description="Enable TOC enhancement")
    meta_data_filter: Dict[str, Any] = Field(default_factory=dict, description="Metadata filter configuration")


class RetrievalComponent(StandardizedComponentBase):
    """
    Search knowledge bases for relevant content.

    This component retrieves relevant chunks from configured knowledge bases
    based on the input query, with support for reranking, knowledge graphs,
    and cross-language search.
    """

    component_name = "Retrieval"
    component_version = "2.0.0"
    component_description = "Search knowledge bases for relevant content"

    input_schema = RetrievalInput
    output_schema = RetrievalOutput
    config_schema = RetrievalConfig

    def run(self, inputs: RetrievalInput) -> RetrievalOutput:
        """
        Execute retrieval search.

        Args:
            inputs: Validated retrieval input with query and options

        Returns:
            Retrieval output with chunks and references
        """
        if self.check_if_canceled("Retrieval processing"):
            return RetrievalOutput()

        # Handle empty query
        if not inputs.query:
            return RetrievalOutput(formalized_content=self.config.empty_response)

        # Resolve knowledge base IDs
        kb_ids = self._resolve_kb_ids()
        if not kb_ids:
            raise Exception("No dataset is selected.")

        # Get knowledge bases
        kbs = KnowledgebaseService.get_by_ids(kb_ids)
        if not kbs:
            raise Exception("No dataset is selected.")

        # Validate embedding models
        embd_nms = list(set([kb.embd_id for kb in kbs]))
        if len(embd_nms) != 1:
            raise AssertionError("Knowledge bases use different embedding models.")

        # Initialize models
        embd_mdl = LLMBundle(
            self._canvas.get_tenant_id(),
            LLMType.EMBEDDING,
            embd_nms[0]
        ) if embd_nms else None

        rerank_mdl = None
        if self.config.rerank_id:
            rerank_mdl = LLMBundle(
                kbs[0].tenant_id,
                LLMType.RERANK,
                self.config.rerank_id
            )

        # Process query
        query = self._process_query(inputs.query)

        # Apply metadata filters
        doc_ids = self._apply_metadata_filters(kb_ids, query)

        # Apply cross-language translation
        if self.config.cross_languages and kbs:
            query = cross_languages(
                kbs[0].tenant_id,
                None,
                query,
                self.config.cross_languages
            )

        # Perform retrieval
        kbinfos = self._perform_retrieval(
            query, embd_mdl, rerank_mdl, kbs, kb_ids, doc_ids
        )

        if self.check_if_canceled("Retrieval processing"):
            return RetrievalOutput()

        # Apply TOC enhancement
        if self.config.toc_enhance and kbinfos.get("chunks"):
            kbinfos = self._apply_toc_enhancement(query, kbinfos, kbs)

        # Apply knowledge graph retrieval
        if self.config.use_kg and kbs:
            kbinfos = self._apply_kg_retrieval(query, kbinfos, kbs, kb_ids, embd_mdl)

        # Clean up chunks
        self._clean_chunks(kbinfos)

        # Handle empty results
        if not kbinfos.get("chunks"):
            return RetrievalOutput(formalized_content=self.config.empty_response)

        # Format output
        json_output = kbinfos["chunks"].copy()
        self._canvas.add_reference(kbinfos["chunks"], kbinfos.get("doc_aggs", []))
        formalized_content = "\n".join(kb_prompt(kbinfos, 200000, True))

        return RetrievalOutput(
            chunks=kbinfos["chunks"],
            total=len(kbinfos["chunks"]),
            references=[c.get("docnm_kwd", c.get("doc_name", "")) for c in kbinfos["chunks"]],
            formalized_content=formalized_content,
            json_output=json_output,
        )

    def _resolve_kb_ids(self) -> List[str]:
        """Resolve knowledge base IDs from config and variable references."""
        kb_ids = []

        for kb_id in self.config.kb_ids:
            if "@" not in kb_id:
                kb_ids.append(kb_id)
                continue

            # Resolve variable reference
            kb_nm = self.get_variable_value(kb_id)
            kb_nm_list = kb_nm if isinstance(kb_nm, list) else [kb_nm]

            for nm_or_id in kb_nm_list:
                e, kb = KnowledgebaseService.get_by_name(
                    nm_or_id,
                    self._canvas._tenant_id
                )
                if not e:
                    e, kb = KnowledgebaseService.get_by_id(nm_or_id)
                    if not e:
                        raise Exception(f"Dataset({nm_or_id}) does not exist.")
                kb_ids.append(kb.id)

        return list(set([kb_id for kb_id in kb_ids if kb_id]))

    def _process_query(self, query: str) -> str:
        """Process query with variable substitution."""
        # Extract variables from query
        variable_ref_patt = r"\{* *\{([a-zA-Z:0-9]+@[A-Za-z0-9_.]+|sys\.[A-Za-z0-9_.]+|env\.[A-Za-z0-9_.]+)\} *\}*"
        vars_dict = {}

        for match in re.finditer(variable_ref_patt, query, flags=re.IGNORECASE | re.DOTALL):
            exp = match.group(1)
            vars_dict[exp] = self.get_variable_value(exp)

        # Substitute variables
        processed = query
        for name, value in vars_dict.items():
            pattern = r"\{%s\}" % re.escape(name)
            replacement = str(value) if value is not None else ""
            processed = re.sub(pattern, replacement, processed)

        # Clean up query
        processed = re.sub(r"^user[::\s]*", "", processed, flags=re.IGNORECASE)

        return processed

    def _apply_metadata_filters(self, kb_ids: List[str], query: str) -> Optional[List[str]]:
        """Apply metadata filters to get document IDs."""
        if not self.config.meta_data_filter:
            return None

        doc_ids = []
        metas = DocumentService.get_meta_by_kbs(kb_ids)
        method = self.config.meta_data_filter.get("method")

        if method == "auto":
            chat_mdl = LLMBundle(self._canvas.get_tenant_id(), LLMType.CHAT)
            filters = gen_meta_filter(chat_mdl, metas, query)
            doc_ids.extend(meta_filter(metas, filters))

        elif method == "manual":
            filters = self.config.meta_data_filter.get("manual", [])

            # Process variable references in filter values
            variable_ref_patt = r"\{* *\{([a-zA-Z:0-9]+@[A-Za-z0-9_.]+|sys\.[A-Za-z0-9_.]+|env\.[A-Za-z0-9_.]+)\} *\}*"

            for flt in filters:
                s = flt.get("value", "")
                pat = re.compile(variable_ref_patt)
                out_parts = []
                last = 0

                for m in pat.finditer(s):
                    out_parts.append(s[last:m.start()])
                    key = m.group(1)
                    v = self.get_variable_value(key)

                    if v is None:
                        rep = ""
                    elif isinstance(v, partial):
                        buf = []
                        for chunk in v():
                            buf.append(chunk)
                        rep = "".join(buf)
                    elif isinstance(v, str):
                        rep = v
                    else:
                        rep = json.dumps(v, ensure_ascii=False)

                    out_parts.append(rep)
                    last = m.end()

                out_parts.append(s[last:])
                flt["value"] = "".join(out_parts)

            doc_ids.extend(meta_filter(metas, filters))

        return doc_ids if doc_ids else None

    def _perform_retrieval(
        self,
        query: str,
        embd_mdl,
        rerank_mdl,
        kbs,
        kb_ids: List[str],
        doc_ids: Optional[List[str]]
    ) -> dict:
        """Perform the main retrieval operation."""
        if not kbs:
            return {"chunks": [], "doc_aggs": []}

        return settings.retriever.retrieval(
            query,
            embd_mdl,
            [kb.tenant_id for kb in kbs],
            kb_ids,
            1,
            self.config.top_n,
            self.config.similarity_threshold,
            1 - self.config.keywords_similarity_weight,
            doc_ids=doc_ids,
            aggs=False,
            rerank_mdl=rerank_mdl,
            rank_feature=label_question(query, kbs),
        )

    def _apply_toc_enhancement(self, query: str, kbinfos: dict, kbs) -> dict:
        """Apply table of contents enhancement."""
        chat_mdl = LLMBundle(self._canvas._tenant_id, LLMType.CHAT)
        cks = settings.retriever.retrieval_by_toc(
            query,
            kbinfos["chunks"],
            [kb.tenant_id for kb in kbs],
            chat_mdl,
            self.config.top_n
        )

        if self.check_if_canceled("TOC enhancement"):
            return kbinfos

        if cks:
            kbinfos["chunks"] = cks

        return kbinfos

    def _apply_kg_retrieval(
        self,
        query: str,
        kbinfos: dict,
        kbs,
        kb_ids: List[str],
        embd_mdl
    ) -> dict:
        """Apply knowledge graph retrieval."""
        ck = settings.kg_retriever.retrieval(
            query,
            [kb.tenant_id for kb in kbs],
            kb_ids,
            embd_mdl,
            LLMBundle(self._canvas.get_tenant_id(), LLMType.CHAT)
        )

        if self.check_if_canceled("KG retrieval"):
            return kbinfos

        if ck.get("content_with_weight"):
            ck["content"] = ck["content_with_weight"]
            del ck["content_with_weight"]
            kbinfos["chunks"].insert(0, ck)

        return kbinfos

    def _clean_chunks(self, kbinfos: dict) -> None:
        """Remove unnecessary fields from chunks."""
        for chunk in kbinfos.get("chunks", []):
            chunk.pop("vector", None)
            chunk.pop("content_ltks", None)

    def thoughts(self) -> str:
        """Return current thinking message."""
        return f"""
Keywords: {getattr(self, '_current_query', '-_-!')}
Looking for the most relevant articles.
        """
