import os
import joblib
import numpy as np

class TurnoutPredictor:
    def __init__(self):
        model_path = os.path.join(os.path.dirname(__file__), 'models', 'turnout_model.pkl')
        self.model = joblib.load(model_path) if os.path.exists(model_path) else None

    def predict(self, total_eligible, prev_turnout, num_candidates, duration_hours, prev_participation_rate):
        if not self.model:
            return 75.0
        features = np.array([[total_eligible, prev_turnout, num_candidates, duration_hours, prev_participation_rate]])
        return round(float(self.model.predict(features)[0]), 2)