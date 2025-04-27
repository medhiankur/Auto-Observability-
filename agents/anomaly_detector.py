import numpy as np
from pyod.models.iforest import IForest
from typing import List, Dict
import pandas as pd

class AnomalyDetector:
    def __init__(self, contamination: float = 0.1):
        self.model = IForest(contamination=contamination, random_state=42)
        self.is_fitted = False

    def _prepare_features(self, logs: List[Dict]) -> pd.DataFrame:
        """Convert log entries to numerical features with robust handling of missing values"""
        df = pd.DataFrame(logs)
        
        # Ensure required columns exist
        required_columns = ['timestamp', 'level', 'service', 'message']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
            
        # Convert categorical columns to numerical
        df['level_code'] = pd.Categorical(df['level']).codes
        df['service_code'] = pd.Categorical(df['service']).codes
        
        # Extract numerical values safely
        def safe_extract_number(value):
            if pd.isna(value):
                return 0
            if isinstance(value, str):
                # Extract first number from string
                import re
                numbers = re.findall(r'\d+(?:\.\d+)?', value)
                return float(numbers[0]) if numbers else 0
            return float(value) if value else 0

        # Safely convert percentage strings and other numerical fields
        df['cpu_usage'] = df['cpu_usage'].apply(safe_extract_number)
        df['memory_usage'] = df['memory_usage'].str.rstrip('%').apply(safe_extract_number)
        df['response_time'] = df['response_time'].str.rstrip('ms').apply(safe_extract_number)
        df['execution_time'] = df['execution_time'].str.rstrip('ms').apply(safe_extract_number)

        # Add error indicators
        df['has_error'] = df['level'].isin(['ERROR', 'CRITICAL', 'WARNING']).astype(int)
        df['is_blocked'] = df['message'].str.contains('blocked', case=False, na=False).astype(int)
        
        features = ['level_code', 'service_code', 'cpu_usage', 'memory_usage', 
                   'response_time', 'execution_time', 'has_error', 'is_blocked']
                   
        return df[features].fillna(0)

    def fit(self, logs: List[Dict]):
        """Train the anomaly detection model"""
        if not logs:
            return
            
        try:
            X = self._prepare_features(logs)
            self.model.fit(X)
            self.is_fitted = True
        except Exception as e:
            print(f"Error fitting model: {str(e)}")
            self.is_fitted = False

    def detect(self, logs: List[Dict]) -> List[Dict]:
        """Detect anomalies in new logs with robust error handling"""
        if not logs:
            return []
            
        try:
            X = self._prepare_features(logs)
            
            # Fit on current batch if model not trained
            if not self.is_fitted:
                self.fit(logs)
                
            if not self.is_fitted:  # If fitting failed
                return []
                
            # Get anomaly scores and labels
            scores = self.model.decision_function(X)
            labels = self.model.predict(X)
            
            anomalies = []
            for idx, (log, score, label) in enumerate(zip(logs, scores, labels)):
                if label == 1:  # Anomaly detected
                    anomaly = log.copy()
                    # Convert timestamp to ISO format string if it's a pandas Timestamp
                    if 'timestamp' in anomaly and isinstance(anomaly['timestamp'], pd.Timestamp):
                        anomaly['timestamp'] = anomaly['timestamp'].isoformat()
                    anomaly.update({
                        'anomaly_score': float(score),
                        'anomaly_features': X.iloc[idx].to_dict()
                    })
                    anomalies.append(anomaly)
                    
            return anomalies
        except Exception as e:
            print(f"Error detecting anomalies: {str(e)}")
            return []