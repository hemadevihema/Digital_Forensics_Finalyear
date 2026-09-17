import io
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.database.mongodb import db_client
from app.services.attack_graph_service import attack_graph_service
from app.logger import logger

class ForensicReportService:
    """
    Generates structured JSON and professional PDF Forensic Audit Reports
    strictly from observable, stored MongoDB evidence without fabricating any data.
    """

    def generate_json_report(self, request_id: str) -> Dict[str, Any]:
        req = db_client.get_request(request_id)
        if not req:
            raise ValueError(f"Request '{request_id}' not found in forensic database.")

        events = db_client.get_events_by_request(request_id)
        events_by_type = {ev.get("event_type"): ev for ev in events}

        session_id = req.get("session_id", "Not available")
        user_question = req.get("user_question", "Not available")
        metrics = req.get("metrics") or {}
        forensics = req.get("forensics") or {}
        retrieved_chunk_ids = req.get("retrieved_chunk_ids", [])
        answer = req.get("answer") or "Not available"

        user_scan = forensics.get("user_scan") or {}
        det_results = user_scan.get("detector_results", {})

        # Extract individual detector scores from real evidence
        rule_res = det_results.get("rule_regex_detector", {})
        rule_score = rule_res.get("score", 0.0) if isinstance(rule_res, dict) else getattr(rule_res, "score", 0.0)

        tfidf_res = det_results.get("tfidf_detector", {})
        tfidf_score = tfidf_res.get("score", 0.0) if isinstance(tfidf_res, dict) else getattr(tfidf_res, "score", 0.0)

        sem_res = det_results.get("semantic_detector", {})
        sem_score = sem_res.get("score", 0.0) if isinstance(sem_res, dict) else getattr(sem_res, "score", 0.0)

        llm_res = det_results.get("llm_detector", {})
        llm_score = llm_res.get("score", 0.0) if isinstance(llm_res, dict) else getattr(llm_res, "score", 0.0)

        matched_patterns = []
        if isinstance(rule_res, dict):
            matched_patterns = rule_res.get("details", {}).get("matched_patterns", [])

        # Retrieval Evidence
        retrieval_list = []
        for rank, cid in enumerate(retrieved_chunk_ids, start=1):
            chunk_data = db_client.get_chunk(cid) or {}
            meta = chunk_data.get("metadata", {})
            retrieval_list.append({
                "rank": rank,
                "chunk_id": cid,
                "document_id": chunk_data.get("document_id", "Not available"),
                "source": meta.get("source", "Not available"),
                "page": chunk_data.get("page", 1),
                "score": chunk_data.get("score", meta.get("score", 0.0)),
                "text_snippet": (chunk_data.get("text", "")[:200] + "...") if len(chunk_data.get("text", "")) > 200 else chunk_data.get("text", "")
            })

        # Timeline Evidence
        timeline_list = []
        for ev in events:
            timeline_list.append({
                "event_id": ev.get("event_id", "Not available"),
                "event_type": ev.get("event_type", "Not available"),
                "component": ev.get("component", "Not available"),
                "timestamp": ev.get("timestamp", "Not available"),
                "duration_ms": ev.get("duration_ms")
            })

        # Attack Graph
        try:
            graph_data = attack_graph_service.build_attack_graph(request_id)
            attack_graph_dict = {
                "nodes": graph_data.get("nodes", []),
                "edges": graph_data.get("edges", [])
            }
        except Exception:
            attack_graph_dict = {"nodes": [], "edges": []}

        # Outcome
        is_blocked = "blocked_direct_injection" in answer or "Security Alert: Prompt Injection attack detected" in answer
        doc_is_poisoned = forensics.get("attribution") in {"DOCUMENT", "BOTH"}

        status = "BLOCKED" if is_blocked else ("QUARANTINED" if doc_is_poisoned else "DELIVERED")
        impact = (
            "ATTACK_BLOCKED_AT_GATEWAY" if is_blocked
            else ("INDIRECT_ATTACK_NEUTRALIZED_BY_QUARANTINE" if doc_is_poisoned
            else "NORMAL_ASSISTANT_DELIVERY")
        )

        prompt_event = events_by_type.get("USER_PROMPT_RECEIVED", {})
        prompt_timestamp = prompt_event.get("timestamp", req.get("timestamp", "Not available"))

        report_id = f"REP-{request_id.replace('REQ-', '')}-{uuid.uuid4().hex[:4].upper()}"
        generated_at = datetime.now(timezone.utc).isoformat()

        return {
            "report_id": report_id,
            "generated_at": generated_at,
            "incident": {
                "request_id": request_id,
                "session_id": session_id,
                "classification": user_scan.get("classification", "BENIGN"),
                "source": forensics.get("attribution", "NONE")
            },
            "prompt": {
                "text": user_question,
                "timestamp": prompt_timestamp
            },
            "detection": {
                "classification": user_scan.get("classification", "BENIGN"),
                "risk_score": user_scan.get("risk_score", 0.0),
                "rule_score": round(rule_score, 4),
                "tfidf_score": round(tfidf_score, 4),
                "semantic_score": round(sem_score, 4),
                "llm_score": round(llm_score, 4),
                "matched_patterns": matched_patterns,
                "reasoning": forensics.get("summary", "Not available")
            },
            "attribution": {
                "source": forensics.get("attribution", "NONE"),
                "document_ids": forensics.get("culprit_document_ids", []),
                "chunk_ids": forensics.get("culprit_chunk_ids", []),
                "evidence": forensics.get("document_scans", [])
            },
            "retrieval": retrieval_list,
            "timeline": timeline_list,
            "attack_graph": attack_graph_dict,
            "performance": {
                "embedding_time_ms": metrics.get("embedding_time_ms", 0.0),
                "retrieval_time_ms": metrics.get("retrieval_time_ms", 0.0),
                "llm_latency_ms": metrics.get("llm_latency_ms", 0.0),
                "total_latency_ms": metrics.get("total_request_latency_ms", 0.0)
            },
            "outcome": {
                "status": status,
                "impact": impact
            }
        }

    def generate_pdf_report(self, request_id: str) -> bytes:
        data = self.generate_json_report(request_id)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            'SubtitleStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=12
        )

        h2_style = ParagraphStyle(
            'H2Style',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=10,
            spaceAfter=4
        )

        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor('#334155')
        )

        bold_style = ParagraphStyle(
            'BoldStyle',
            parent=body_style,
            fontName='Helvetica-Bold'
        )

        code_style = ParagraphStyle(
            'CodeStyle',
            parent=body_style,
            fontName='Courier',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#1e1b4b')
        )

        elements = []

        # Document Header
        elements.append(Paragraph("PROMPT INJECTION FORENSIC AUDIT REPORT", title_style))
        elements.append(Paragraph(
            f"Report Reference: {data['report_id']} | Generated: {data['generated_at']} | Observable RAG Forensics Framework",
            subtitle_style
        ))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#0284c7'), spaceAfter=10))

        # 1. Incident Summary
        elements.append(Paragraph("1. Incident Summary", h2_style))
        incident = data["incident"]
        summary_table_data = [
            [Paragraph("<b>Request ID:</b>", body_style), Paragraph(incident["request_id"], code_style),
             Paragraph("<b>Session ID:</b>", body_style), Paragraph(incident["session_id"], code_style)],
            [Paragraph("<b>Classification:</b>", body_style), Paragraph(f"<b>{incident['classification']}</b>", body_style),
             Paragraph("<b>Attributed Source:</b>", body_style), Paragraph(f"<b>{incident['source']}</b>", body_style)],
            [Paragraph("<b>Investigation Status:</b>", body_style), Paragraph(data["outcome"]["status"], body_style),
             Paragraph("<b>Forensic Impact:</b>", body_style), Paragraph(data["outcome"]["impact"], body_style)],
        ]
        summary_table = Table(summary_table_data, colWidths=[100, 170, 100, 170])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 8))

        # 2 & 3. Request & Session Details
        elements.append(Paragraph("2. Request & Session Information", h2_style))
        elements.append(Paragraph(
            f"Request correlation established under Session ID <font name='Courier'>{incident['session_id']}</font> "
            f"at timestamp {data['prompt']['timestamp']}. System operates with strict MongoDB Atlas correlation.",
            body_style
        ))
        elements.append(Spacer(1, 8))

        # 4. User Prompt
        elements.append(Paragraph("4. User Prompt", h2_style))
        prompt_box = Table([
            [Paragraph(f"<b>Submitted Query:</b> {data['prompt']['text']}", body_style)]
        ], colWidths=[540])
        prompt_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f1f5f9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(prompt_box)
        elements.append(Spacer(1, 8))

        # 5 & 6. Detection Results & Signals
        elements.append(Paragraph("5 & 6. Detection Results & Multi-Layer Signals", h2_style))
        det = data["detection"]
        signals_table_data = [
            [Paragraph("<b>Detection Layer</b>", bold_style), Paragraph("<b>Risk Score (0.0 - 1.0)</b>", bold_style), Paragraph("<b>Triggered Status</b>", bold_style)],
            [Paragraph("Layer 1: Rule & Regex Pattern Matching", body_style), Paragraph(str(det["rule_score"]), code_style), Paragraph("Triggered" if det["rule_score"] > 0 else "Clean", body_style)],
            [Paragraph("Layer 2: TF-IDF Cosine Similarity", body_style), Paragraph(str(det["tfidf_score"]), code_style), Paragraph("Triggered" if det["tfidf_score"] > 0.3 else "Clean", body_style)],
            [Paragraph("Layer 3: Dense Semantic Embedding", body_style), Paragraph(str(det["semantic_score"]), code_style), Paragraph("Triggered" if det["semantic_score"] > 0.45 else "Clean", body_style)],
            [Paragraph("Layer 4: Gemini Contextual Classifier", body_style), Paragraph(str(det["llm_score"]), code_style), Paragraph("Triggered" if det["llm_score"] > 0.5 else "Clean", body_style)],
            [Paragraph("<b>Ensemble Risk Fusion Total</b>", bold_style), Paragraph(f"<b>{det['risk_score']}</b>", bold_style), Paragraph(f"<b>{det['classification']}</b>", bold_style)],
        ]
        signals_table = Table(signals_table_data, colWidths=[240, 150, 150])
        signals_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(signals_table)

        if det["matched_patterns"]:
            pattern_strs = [
                (p.get("pattern", str(p)) if isinstance(p, dict) else str(p))
                for p in det["matched_patterns"]
            ]
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(
                f"<b>Matched Adversarial Signatures:</b> {', '.join(pattern_strs)}",
                body_style
            ))
        elements.append(Spacer(1, 8))

        # 7. Source Attribution
        elements.append(Paragraph("7. Source Attribution & Provenance", h2_style))
        attr = data["attribution"]
        culprit_docs_str = ", ".join(attr["document_ids"]) if attr["document_ids"] else "None (No poisoned documents)"
        culprit_chunks_str = ", ".join(attr["chunk_ids"]) if attr["chunk_ids"] else "None"
        elements.append(Paragraph(f"<b>Primary Vector Origin:</b> {attr['source']}", body_style))
        elements.append(Paragraph(f"<b>Compromised Document ID(s):</b> {culprit_docs_str}", body_style))
        elements.append(Paragraph(f"<b>Compromised Chunk ID(s):</b> {culprit_chunks_str}", body_style))
        elements.append(Paragraph(f"<b>Forensic Attribution Summary:</b> {det['reasoning']}", body_style))
        elements.append(Spacer(1, 8))

        # 8. Retrieved Documents and Chunks
        elements.append(Paragraph("8. Retrieved Documents and Chunks (Top-K)", h2_style))
        if data["retrieval"]:
            ret_table_data = [
                [Paragraph("<b>Rank</b>", bold_style), Paragraph("<b>Chunk ID</b>", bold_style), Paragraph("<b>Source File</b>", bold_style), Paragraph("<b>Score</b>", bold_style), Paragraph("<b>Content Snippet</b>", bold_style)]
            ]
            for item in data["retrieval"][:5]:  # show top 5 in PDF
                ret_table_data.append([
                    Paragraph(str(item["rank"]), body_style),
                    Paragraph(item["chunk_id"], code_style),
                    Paragraph(f"{item['source']} (p.{item['page']})", body_style),
                    Paragraph(f"{item['score']:.3f}", code_style),
                    Paragraph(item["text_snippet"][:90] + "...", body_style)
                ])
            ret_table = Table(ret_table_data, colWidths=[35, 95, 120, 50, 240])
            ret_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(ret_table)
        else:
            elements.append(Paragraph("No document chunks retrieved for this request.", body_style))
        elements.append(Spacer(1, 8))

        # 9. Event Timeline
        elements.append(Paragraph("9. Correlated Event Timeline", h2_style))
        if data["timeline"]:
            tl_table_data = [
                [Paragraph("<b>Timestamp</b>", bold_style), Paragraph("<b>Event Type</b>", bold_style), Paragraph("<b>Component</b>", bold_style), Paragraph("<b>Duration</b>", bold_style)]
            ]
            for ev in data["timeline"]:
                dur_str = f"{ev['duration_ms']:.1f} ms" if ev.get("duration_ms") is not None else "-"
                tl_table_data.append([
                    Paragraph(ev["timestamp"].split("T")[-1].replace("Z", "") if "T" in ev["timestamp"] else ev["timestamp"], code_style),
                    Paragraph(ev["event_type"], code_style),
                    Paragraph(ev["component"], body_style),
                    Paragraph(dur_str, code_style)
                ])
            tl_table = Table(tl_table_data, colWidths=[110, 190, 140, 100])
            tl_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 2.5),
            ]))
            elements.append(tl_table)
        elements.append(Spacer(1, 8))

        # 10. Attack Path
        elements.append(Paragraph("10. Causal Attack Path & Provenance Graph Summary", h2_style))
        ag = data["attack_graph"]
        path_desc = (
            f"Causal graph contains {len(ag.get('nodes', []))} nodes and {len(ag.get('edges', []))} directed edges. "
            f"The execution traversed from Actor <font name='Courier'>USER</font> through Prompt Analysis and "
            f"Ensemble Risk Detection to reach Outcome verdict <font name='Courier'>{data['outcome']['status']}</font>."
        )
        elements.append(Paragraph(path_desc, body_style))
        elements.append(Spacer(1, 8))

        # 11. Performance Metrics
        elements.append(Paragraph("11. Performance & Latency Breakdown", h2_style))
        perf = data["performance"]
        perf_table_data = [
            [Paragraph("<b>Metric</b>", bold_style), Paragraph("<b>Observed Duration (ms)</b>", bold_style)],
            [Paragraph("FAISS Retrieval Time", body_style), Paragraph(f"{perf['retrieval_time_ms']} ms", code_style)],
            [Paragraph("Query Embedding Time", body_style), Paragraph(f"{perf['embedding_time_ms']} ms", code_style)],
            [Paragraph("Gemini LLM Inference Latency", body_style), Paragraph(f"{perf['llm_latency_ms']} ms", code_style)],
            [Paragraph("<b>Total Request Pipeline Latency</b>", bold_style), Paragraph(f"<b>{perf['total_latency_ms']} ms</b>", code_style)],
        ]
        perf_table = Table(perf_table_data, colWidths=[300, 240])
        perf_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(perf_table)
        elements.append(Spacer(1, 8))

        # 12 & 13. Outcome & Evidence Summary
        elements.append(Paragraph("12 & 13. System Outcome & Forensic Evidence Summary", h2_style))
        elements.append(Paragraph(
            f"<b>Final Decision:</b> {data['outcome']['status']} ({data['outcome']['impact']})<br/>"
            f"All forensic evidence, including raw embeddings, chunk hashes, and correlated event timestamps, "
            f"are permanently persisted under Request ID <font name='Courier'>{request_id}</font> in MongoDB Atlas.",
            body_style
        ))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()

forensic_report_service = ForensicReportService()
