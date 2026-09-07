import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor, IsolationForest

MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

def train_turnout_model():
    np.random.seed(42)
    samples = 500
    df = pd.DataFrame({
        'total_eligible': np.random.randint(100, 2000, size=samples),
        'prev_turnout': np.random.uniform(40.0, 95.0, size=samples),
        'num_candidates': np.random.randint(2, 10, size=samples),
        'duration_hours': np.random.randint(4, 72, size=samples),
        'prev_participation_rate': np.random.uniform(0.3, 0.95, size=samples),
    })
    df['turnout_pct'] = np.clip(
        0.4 * df['prev_turnout'] + 25 * df['prev_participation_rate'] + 1.2 * df['num_candidates'] + np.random.normal(0, 3, size=samples),
        20.0, 98.0
    )
    
    X = df[['total_eligible', 'prev_turnout', 'num_candidates', 'duration_hours', 'prev_participation_rate']]
    y = df['turnout_pct']
    
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X, y)
    joblib.dump(model, os.path.join(MODEL_DIR, 'turnout_model.pkl'))

def train_anomaly_model():
    np.random.seed(42)
    normal_votes = np.random.normal(loc=[3, 0.9, 1], scale=[1, 0.05, 0.5], size=(1000, 3))
    model = IsolationForest(contamination=0.03, random_state=42)
    model.fit(normal_votes)
    joblib.dump(model, os.path.join(MODEL_DIR, 'anomaly_model.pkl'))

if __name__ == '__main__':
    train_turnout_model()
    train_anomaly_model()
    print("ML models successfully trained and saved!")