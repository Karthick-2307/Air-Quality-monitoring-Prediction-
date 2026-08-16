
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import db

def evaluate_models():
    metrics = db.get_model_metrics()

    if not metrics:
        print("❌ No model metrics found. Train models first with: python -m ml.train_model")
        return None

    print("=" * 60)
    print("Model Evaluation Metrics")
    print("=" * 60)
    print(f"{'Model':<20} {'MAE':<10} {'RMSE':<10} {'R²':<10} {'Trained At'}")
    print("-" * 60)

    for m in metrics:
        print(f"{m['model_name']:<20} {m['mae']:<10.2f} {m['rmse']:<10.2f} {m['r2']:<10.4f} {m['trained_at']}")

    if metrics:
        best = min(metrics, key=lambda m: m["rmse"])
        print("-" * 60)
        print(f"⭐ Best model: {best['model_name']} (RMSE: {best['rmse']:.2f})")

    return metrics

if __name__ == "__main__":
    evaluate_models()
