from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import networkx as nx

from app.database.mongodb import db_client
from app.logger import logger

class AttackGraphService:
    """
    Constructs a causal Directed Acyclic Graph (DAG) using NetworkX from real request,
    retrieval, detection, attribution, and lifecycle event evidence.
    Converts the graph into a structured JSON representation for API clients and React Flow.
    """

    def build_attack_graph(self, request_id: str) -> Dict[str, Any]:
        req = db_client.get_request(request_id)
        if not req:
            raise ValueError(f"Request '{request_id}' not found in forensic database.")

        events = db_client.get_events_by_request(request_id)
        events_by_type = {ev.get("event_type"): ev for ev in events}

        session_id = req.get("session_id", "UNKNOWN_SESSION")
        user_question = req.get("user_question", "")
        retrieved_chunk_ids = req.get("retrieved_chunk_ids", [])
        forensics = req.get("forensics") or {}
        metrics = req.get("metrics") or {}
        answer = req.get("answer") or ""

        attribution_source = forensics.get("attribution", "NONE")
        user_scan = forensics.get("user_scan") or {}
        doc_scans = forensics.get("document_scans") or []
        culprit_chunks = set(forensics.get("culprit_chunk_ids") or [])
        culprit_docs = set(forensics.get("culprit_document_ids") or [])

        user_is_malicious = attribution_source in {"USER", "BOTH"}
        doc_is_malicious = attribution_source in {"DOCUMENT", "BOTH"}

        # Initialize directed graph
        G = nx.DiGraph()

        # 1. USER Node
        user_node_id = f"user_{session_id}"
        G.add_node(
            user_node_id,
            id=user_node_id,
            type="USER",
            label="User Client",
            is_malicious=user_is_malicious,
            risk_level="HIGH" if user_is_malicious else "LOW",
            metadata={
                "session_id": session_id,
                "role": "Client Actor",
                "timestamp": req.get("timestamp")
            }
        )

        # 2. USER_PROMPT Node
        prompt_node_id = f"prompt_{request_id}"
        prompt_event = events_by_type.get("USER_PROMPT_RECEIVED", {})
        G.add_node(
            prompt_node_id,
            id=prompt_node_id,
            type="USER_PROMPT",
            label=f"User Prompt: \"{user_question[:40]}...\"" if len(user_question) > 40 else f"User Prompt: \"{user_question}\"",
            is_malicious=user_is_malicious,
            risk_level="HIGH" if user_is_malicious else "LOW",
            metadata={
                "text": user_question,
                "char_length": len(user_question),
                "timestamp": prompt_event.get("timestamp", req.get("timestamp"))
            }
        )
        G.add_edge(user_node_id, prompt_node_id, label="SUBMITS", relation="originates")

        # 3. RETRIEVAL Node (if retrieval happened or chunks exist)
        retrieval_node_id = f"retrieval_{request_id}"
        retrieval_event = events_by_type.get("RETRIEVAL_COMPLETED") or events_by_type.get("RETRIEVAL_STARTED")
        if retrieved_chunk_ids or retrieval_event:
            G.add_node(
                retrieval_node_id,
                id=retrieval_node_id,
                type="RETRIEVAL",
                label=f"FAISS Retrieval (Top-{len(retrieved_chunk_ids)})",
                is_malicious=False,
                risk_level="LOW",
                metadata={
                    "retrieved_count": len(retrieved_chunk_ids),
                    "latency_ms": metrics.get("retrieval_time_ms", 0.0),
                    "timestamp": retrieval_event.get("timestamp") if retrieval_event else None
                }
            )
            G.add_edge(prompt_node_id, retrieval_node_id, label="TRIGGERS_QUERY", relation="invokes")

        # 4. DOCUMENT & CHUNK Nodes
        doc_scans_map = {ds.get("chunk_id"): ds for ds in doc_scans}
        doc_nodes_created = set()

        for rank, cid in enumerate(retrieved_chunk_ids, start=1):
            chunk_data = db_client.get_chunk(cid) or {}
            doc_id = chunk_data.get("document_id", "DOC-UNKNOWN")
            meta = chunk_data.get("metadata", {})
            source_filename = meta.get("source", "Document")
            page_num = chunk_data.get("page", 1)
            is_chunk_poisoned = cid in culprit_chunks
            chunk_scan_info = doc_scans_map.get(cid, {})

            # Add Parent Document Node if not already added
            doc_node_id = f"doc_{doc_id}"
            if doc_node_id not in doc_nodes_created:
                is_doc_poisoned = doc_id in culprit_docs
                doc_record = db_client.get_document(doc_id) or {}
                G.add_node(
                    doc_node_id,
                    id=doc_node_id,
                    type="DOCUMENT",
                    label=f"Doc: {source_filename}",
                    is_malicious=is_doc_poisoned,
                    risk_level="CRITICAL" if is_doc_poisoned else "LOW",
                    metadata={
                        "document_id": doc_id,
                        "filename": source_filename,
                        "file_type": doc_record.get("file_type", "txt"),
                        "page_count": doc_record.get("page_count", 1)
                    }
                )
                doc_nodes_created.add(doc_node_id)

            # Add Chunk Node
            chunk_node_id = f"chunk_{cid}"
            G.add_node(
                chunk_node_id,
                id=chunk_node_id,
                type="CHUNK",
                label=f"{source_filename} — Chunk {cid} (p.{page_num})",
                is_malicious=is_chunk_poisoned,
                risk_level="CRITICAL" if is_chunk_poisoned else "LOW",
                metadata={
                    "document_id": doc_id,
                    "chunk_id": cid,
                    "page": page_num,
                    "rank": rank,
                    "similarity_score": chunk_data.get("score", meta.get("score", 0.0)),
                    "text_preview": (chunk_data.get("text", "")[:120] + "...") if len(chunk_data.get("text", "")) > 120 else chunk_data.get("text", ""),
                    "matched_patterns": chunk_scan_info.get("matched_patterns", []),
                    "risk_score": chunk_scan_info.get("risk_score", 0.0)
                }
            )

            # Connect Document -> Chunk
            G.add_edge(doc_node_id, chunk_node_id, label="CONTAINS", relation="hierarchy")

            # Connect Retrieval -> Chunk
            if retrieval_node_id in G:
                G.add_edge(retrieval_node_id, chunk_node_id, label="RETRIEVES", relation="data_flow")

        # 5. CONTEXT Node (Untrusted quarantine boundary)
        context_node_id = f"context_{request_id}"
        context_event = events_by_type.get("CONTEXT_BUILT")
        is_context_compromised = doc_is_malicious or user_is_malicious
        G.add_node(
            context_node_id,
            id=context_node_id,
            type="CONTEXT",
            label="Quarantined Context Boundary",
            is_malicious=is_context_compromised,
            risk_level="HIGH" if is_context_compromised else "LOW",
            metadata={
                "boundary_type": "System Prompt || Untrusted Data || User Question",
                "chunks_count": len(retrieved_chunk_ids),
                "timestamp": context_event.get("timestamp") if context_event else None
            }
        )

        G.add_edge(prompt_node_id, context_node_id, label="FEEDS_QUERY", relation="merges")
        for cid in retrieved_chunk_ids:
            chunk_node_id = f"chunk_{cid}"
            if chunk_node_id in G:
                G.add_edge(chunk_node_id, context_node_id, label="FEEDS_UNTRUSTED_CHUNK", relation="merges")

        # 6. DETECTION Node (Multi-layer risk fusion)
        detection_node_id = f"detection_{request_id}"
        det_event = events_by_type.get("INJECTION_SCAN_COMPLETED")
        overall_risk = user_scan.get("risk_score", 0.0)
        user_classification = user_scan.get("classification", "BENIGN")
        det_results = user_scan.get("detector_results", {})
        layer_breakdown = {
            k: v.get("score", 0.0) if isinstance(v, dict) else getattr(v, "score", 0.0)
            for k, v in det_results.items()
        }

        G.add_node(
            detection_node_id,
            id=detection_node_id,
            type="DETECTION",
            label=f"Forensic Scan: {user_classification} ({overall_risk:.2f})",
            is_malicious=overall_risk >= 0.35,
            risk_level="CRITICAL" if overall_risk >= 0.70 else ("HIGH" if overall_risk >= 0.35 else "LOW"),
            metadata={
                "risk_score": overall_risk,
                "classification": user_classification,
                "layer_scores": layer_breakdown,
                "triggered_layers": user_scan.get("forensic_evidence", {}).get("triggered_layers", []),
                "scan_latency_ms": metrics.get("injection_scan_time_ms", 0.0),
                "timestamp": det_event.get("timestamp") if det_event else None
            }
        )

        G.add_edge(prompt_node_id, detection_node_id, label="SCANS_USER_INPUT", relation="analyzes")
        for cid in culprit_chunks:
            chunk_node_id = f"chunk_{cid}"
            if chunk_node_id in G:
                G.add_edge(chunk_node_id, detection_node_id, label="SCANS_POISONED_CHUNK", relation="analyzes")

        # 7. ATTRIBUTION Node
        attribution_node_id = f"attribution_{request_id}"
        attr_event = events_by_type.get("INJECTION_ATTRIBUTED")
        G.add_node(
            attribution_node_id,
            id=attribution_node_id,
            type="ATTRIBUTION",
            label=f"Attribution: {attribution_source}",
            is_malicious=attribution_source in {"USER", "DOCUMENT", "BOTH"},
            risk_level="CRITICAL" if attribution_source in {"USER", "DOCUMENT", "BOTH"} else "LOW",
            metadata={
                "source": attribution_source,
                "summary": forensics.get("summary", ""),
                "culprit_chunks": list(culprit_chunks),
                "culprit_documents": list(culprit_docs),
                "timestamp": attr_event.get("timestamp") if attr_event else None
            }
        )
        G.add_edge(detection_node_id, attribution_node_id, label="ATTRIBUTES_PROVENANCE", relation="concludes")

        # 8. LLM_REQUEST & LLM_RESPONSE Nodes (if not blocked or if generation occurred)
        llm_req_event = events_by_type.get("LLM_REQUEST_STARTED")
        llm_res_event = events_by_type.get("LLM_RESPONSE_RECEIVED")

        is_blocked = "blocked_direct_injection" in answer or "Security Alert: Prompt Injection attack detected" in answer

        if not is_blocked and (llm_req_event or answer):
            llm_req_node_id = f"llm_req_{request_id}"
            G.add_node(
                llm_req_node_id,
                id=llm_req_node_id,
                type="LLM_REQUEST",
                label="Gemini LLM Prompt Delivery",
                is_malicious=doc_is_malicious,
                risk_level="HIGH" if doc_is_malicious else "LOW",
                metadata={
                    "model": llm_req_event.get("data", {}).get("model", "gemini-1.5-flash") if llm_req_event else "gemini-1.5-flash",
                    "quarantine_enforced": True,
                    "timestamp": llm_req_event.get("timestamp") if llm_req_event else None
                }
            )
            G.add_edge(context_node_id, llm_req_node_id, label="SUBMITS_TO_MODEL", relation="data_flow")

            llm_res_node_id = f"llm_res_{request_id}"
            G.add_node(
                llm_res_node_id,
                id=llm_res_node_id,
                type="LLM_RESPONSE",
                label="Gemini LLM Generation",
                is_malicious=False,
                risk_level="LOW",
                metadata={
                    "latency_ms": metrics.get("llm_latency_ms", 0.0),
                    "status": "grounded_response",
                    "timestamp": llm_res_event.get("timestamp") if llm_res_event else None
                }
            )
            G.add_edge(llm_req_node_id, llm_res_node_id, label="GENERATES", relation="produces")

        # 9. OUTCOME Node
        outcome_node_id = f"outcome_{request_id}"
        outcome_status = "BLOCKED" if is_blocked else ("QUARANTINED" if doc_is_malicious else "DELIVERED")
        outcome_impact = (
            "ATTACK_BLOCKED_AT_GATEWAY" if is_blocked
            else ("INDIRECT_ATTACK_NEUTRALIZED_BY_QUARANTINE" if doc_is_malicious
            else "NORMAL_ASSISTANT_DELIVERY")
        )

        G.add_node(
            outcome_node_id,
            id=outcome_node_id,
            type="OUTCOME",
            label=f"Outcome: {outcome_status}",
            is_malicious=is_blocked or doc_is_malicious,
            risk_level="CRITICAL" if is_blocked else ("HIGH" if doc_is_malicious else "LOW"),
            metadata={
                "status": outcome_status,
                "impact": outcome_impact,
                "answer_preview": (answer[:140] + "...") if len(answer) > 140 else answer,
                "total_request_latency_ms": metrics.get("total_request_latency_ms", 0.0)
            }
        )

        G.add_edge(attribution_node_id, outcome_node_id, label="GOVERNS_ACTION", relation="enforces")
        if not is_blocked and f"llm_res_{request_id}" in G:
            G.add_edge(f"llm_res_{request_id}", outcome_node_id, label="DELIVERS_RESPONSE", relation="renders")

        # Serialize NetworkX nodes and edges to standard React Flow friendly JSON
        nodes_json: List[Dict[str, Any]] = []
        for n, data in G.nodes(data=True):
            nodes_json.append({
                "id": data["id"],
                "type": data["type"],
                "label": data["label"],
                "is_malicious": data.get("is_malicious", False),
                "risk_level": data.get("risk_level", "LOW"),
                "metadata": data.get("metadata", {})
            })

        edges_json: List[Dict[str, Any]] = []
        for u, v, data in G.edges(data=True):
            edges_json.append({
                "id": f"edge_{u}_to_{v}",
                "source": u,
                "target": v,
                "label": data.get("label", ""),
                "relation": data.get("relation", "")
            })

        return {
            "request_id": request_id,
            "session_id": session_id,
            "classification": user_classification,
            "source": attribution_source,
            "summary": forensics.get("summary", ""),
            "total_nodes": len(nodes_json),
            "total_edges": len(edges_json),
            "nodes": nodes_json,
            "edges": edges_json
        }

attack_graph_service = AttackGraphService()
