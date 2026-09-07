import os
import joblib
import numpy as np

class AnomalyDetector:
    def __init__(self):
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'anomaly_model.pkl')
        self.model = joblib.load(model_path) if os.path.exists(model_path) else None

    def analyze_burst(self, votes_in_1min, unique_ips_ratio, rapid_submissions):
        if not self.model:
            return {"status": "Normal Activity", "flag": False}
        
        pred = self.model.predict(np.array([[votes_in_1min, unique_ips_ratio, rapid_submissions]]))[0]
        if pred == -1:
            return {
                "status": "Potential Anomaly",
                "flag": True,
                "reason": "Unusually high voting velocity detected.",
                "action": "Admin review required."
            }
        return {"status": "Normal Activity", "flag": False}