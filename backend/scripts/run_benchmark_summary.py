import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.detector.evaluator import benchmark_evaluator

def main():
    rep = benchmark_evaluator.run_benchmark(include_llm=False)
    print("\n" + "=" * 92)
    print("PROMPT INJECTION FORENSICS — MEASURED BENCHMARK EVALUATION SUMMARY")
    print(f"Evaluated Samples: {rep['samples_evaluated']} | Benchmark Duration: {rep['total_benchmark_duration_ms']} ms")
    print("=" * 92)
    print(f"{'Detector Layer':<22} | {'Accuracy':<9} | {'Precision':<9} | {'Recall':<9} | {'F1-Score':<9} | {'FPR':<8} | {'FNR':<8} | {'Avg Latency':<12}")
    print("-" * 92)
    for k, m in rep['summary_metrics'].items():
        name_map = {
            "rule_regex": "1. Rule / Regex",
            "tfidf": "2. TF-IDF Cosine",
            "semantic": "3. Semantic Embedding",
            "ensemble": "4. Hybrid Ensemble"
        }
        name = name_map.get(k, k)
        lat = m['latency']['avg_ms']
        print(f"{name:<22} | {m['accuracy']:<9.4f} | {m['precision']:<9.4f} | {m['recall']:<9.4f} | {m['f1_score']:<9.4f} | {m['false_positive_rate']:<8.4f} | {m['false_negative_rate']:<8.4f} | {lat:>8.2f} ms")

    print("\n" + "=" * 65)
    print("SOURCE ATTRIBUTION BENCHMARK PERFORMANCE")
    print("=" * 65)
    print(f"{'Source Vector':<16} | {'Accuracy':<9} | {'Precision':<9} | {'Recall':<9} | {'F1-Score':<9}")
    print("-" * 65)
    for k, m in rep['attribution_metrics'].items():
        print(f"{k:<16} | {m['accuracy']:<9.4f} | {m['precision']:<9.4f} | {m['recall']:<9.4f} | {m['f1_score']:<9.4f}")

    print("\n" + "=" * 65)
    print("LATENCY PROFILING BREAKDOWN (MILLISECONDS)")
    print("=" * 65)
    print(f"{'Component':<22} | {'Average':<10} | {'Minimum':<10} | {'Maximum':<10}")
    print("-" * 65)
    for k, s in rep['latency_profiling'].items():
        print(f"{k:<22} | {s['avg_ms']:>7.2f} ms | {s['min_ms']:>7.2f} ms | {s['max_ms']:>7.2f} ms")

    print("\n" + "=" * 80)
    print("DETECTION THRESHOLD SENSITIVITY SWEEP")
    print("=" * 80)
    sweep = benchmark_evaluator.evaluate_threshold_sweep()
    print(f"{'Threshold':<10} | {'Accuracy':<9} | {'Precision':<9} | {'Recall':<9} | {'F1-Score':<9} | {'FP':<5} | {'FN':<5}")
    print("-" * 80)
    for row in sweep:
        print(f"{row['threshold']:<10.2f} | {row['accuracy']:<9.4f} | {row['precision']:<9.4f} | {row['recall']:<9.4f} | {row['f1_score']:<9.4f} | {row['false_positives']:<5} | {row['false_negatives']:<5}")

if __name__ == "__main__":
    main()
