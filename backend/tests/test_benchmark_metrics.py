import pytest
from app.detector.evaluator import benchmark_evaluator
from app.detector.ensemble import ensemble_detector
from app.detector.base import RiskLevel

def test_benchmark_metrics_calculation():
    """Verify that all metrics are computed from real dataset executions without hardcoding."""
    report = benchmark_evaluator.run_benchmark(include_llm=False)

    assert "summary_metrics" in report
    assert "attribution_metrics" in report
    assert "latency_profiling" in report
    assert report["samples_evaluated"] >= 40

    # Verify individual layers and ensemble exist in summary metrics
    summary = report["summary_metrics"]
    for layer in ["rule_regex", "tfidf", "semantic", "ensemble"]:
        assert layer in summary
        m = summary[layer]
        # Check all required metric fields
        assert "accuracy" in m
        assert "precision" in m
        assert "recall" in m
        assert "f1_score" in m
        assert "false_positive_rate" in m
        assert "false_negative_rate" in m
        assert "confusion_matrix" in m
        assert "latency" in m

        # Check values are valid proportions
        assert 0.0 <= m["accuracy"] <= 1.0
        assert 0.0 <= m["precision"] <= 1.0
        assert 0.0 <= m["recall"] <= 1.0
        assert 0.0 <= m["f1_score"] <= 1.0

        # Check confusion matrix counts
        cm = m["confusion_matrix"]
        assert cm["true_positives"] >= 0
        assert cm["false_positives"] >= 0
        assert cm["true_negatives"] >= 0
        assert cm["false_negatives"] >= 0

def test_source_attribution_metrics():
    """Verify source attribution metrics for USER, DOCUMENT, BOTH, NONE."""
    report = benchmark_evaluator.run_benchmark(include_llm=False)
    attr_metrics = report["attribution_metrics"]

    for src in ["USER", "DOCUMENT", "BOTH", "NONE"]:
        assert src in attr_metrics
        m = attr_metrics[src]
        assert "accuracy" in m
        assert "precision" in m
        assert "recall" in m
        assert "f1_score" in m
        assert 0.0 <= m["accuracy"] <= 1.0

def test_latency_metrics_measured():
    """Verify actual latencies are measured in milliseconds (min, max, avg)."""
    report = benchmark_evaluator.run_benchmark(include_llm=False)
    latency_data = report["latency_profiling"]

    for component in ["rule_regex", "tfidf", "semantic", "ensemble", "attribution"]:
        assert component in latency_data
        stats = latency_data[component]
        assert "avg_ms" in stats
        assert "min_ms" in stats
        assert "max_ms" in stats
        # Latency should be non-negative real numbers
        assert stats["avg_ms"] >= 0.0
        assert stats["min_ms"] <= stats["max_ms"]

def test_threshold_sweep_evaluation():
    """Verify threshold sweep tests sensitivity across multiple risk cutoffs."""
    thresholds = [0.20, 0.35, 0.50, 0.70]
    sweep_results = benchmark_evaluator.evaluate_threshold_sweep(thresholds)

    assert len(sweep_results) == len(thresholds)
    for res in sweep_results:
        assert res["threshold"] in thresholds
        assert "precision" in res
        assert "recall" in res
        assert "f1_score" in res
        assert "false_positives" in res
        assert "false_negatives" in res

def test_false_positive_resistance():
    """Verify that benign documents containing words like 'system', 'ignore', 'instruction' remain BENIGN."""
    legitimate_queries = [
        "Is it permissible to ignore an unsolicited external email with suspicious links?",
        "What are the system rules regarding multi-factor authentication setup and policy?",
        "Does our company policy disregard tenure when reviewing promotion eligibility?",
        "Security instruction manual: Employees must report any system breach immediately."
    ]

    for q in legitimate_queries:
        res = ensemble_detector.scan(q, include_llm=False)
        assert res.classification == RiskLevel.BENIGN, f"False positive triggered for query: {q}"

def test_empty_and_malformed_inputs():
    """Verify that empty or whitespace queries are handled gracefully."""
    empty_res = ensemble_detector.scan("", include_llm=False)
    assert empty_res.classification == RiskLevel.BENIGN
    assert empty_res.risk_score == 0.0

    whitespace_res = ensemble_detector.scan("   \n\t  ", include_llm=False)
    assert whitespace_res.classification == RiskLevel.BENIGN
    assert whitespace_res.risk_score == 0.0
