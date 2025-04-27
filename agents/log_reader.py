import pandas as pd
from pathlib import Path
import json
from typing import Dict, List
from datetime import datetime, timedelta

class LogReader:
    def __init__(self, log_dir: str = "./logs"):
        self.log_dir = Path(log_dir)
        self.cache_file = self.log_dir / "log_cache.json"
        self.last_read_time = None
        self._initialize_cache()

    def _initialize_cache(self):
        if not self.cache_file.exists():
            with open(self.cache_file, 'w') as f:
                json.dump({"last_position": 0, "known_anomalies": []}, f)

    def get_recent_logs(self, minutes: int = 5) -> List[Dict]:
        """Get logs from the last N minutes of available data"""
        try:
            all_logs = []
            for log_file in self.log_dir.glob("*.csv"):
                if log_file.name == "log_cache.json":
                    continue
                    
                df = pd.read_csv(log_file, on_bad_lines='skip')
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                if df.empty:
                    continue
                
                # Use the latest timestamp in the logs as reference
                latest_time = df['timestamp'].max()
                cutoff_time = latest_time - timedelta(minutes=minutes)
                
                recent_logs = df[df['timestamp'] > cutoff_time]
                
                if not recent_logs.empty:
                    all_logs.extend(recent_logs.to_dict('records'))
            
            return all_logs
        except Exception as e:
            print(f"Error reading logs: {str(e)}")
            return []

    def read_new_logs(self, file_pattern: str = "*.csv") -> List[Dict]:
        """Read new logs since last check"""
        try:
            new_logs = []
            for log_file in self.log_dir.glob(file_pattern):
                if log_file.name == "log_cache.json":
                    continue
                    
                df = pd.read_csv(log_file, on_bad_lines='skip')
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                if df.empty:
                    continue
                
                # If no last read time, use the earliest timestamp
                if not self.last_read_time:
                    self.last_read_time = df['timestamp'].min()
                
                new_records = df[df['timestamp'] > self.last_read_time]
                if not new_records.empty:
                    new_logs.extend(new_records.to_dict('records'))
            
            if new_logs:
                self.last_read_time = max(log['timestamp'] for log in new_logs)
            
            return new_logs
        except Exception as e:
            print(f"Error reading new logs: {str(e)}")
            return []

    def mark_anomaly(self, log_entry: Dict):
        """Mark a log entry as an anomaly for future reference"""
        try:
            with open(self.cache_file, 'r') as f:
                cache = json.load(f)
            
            cache["known_anomalies"].append({
                "timestamp": log_entry["timestamp"],
                "service": log_entry["service"],
                "message": log_entry["message"]
            })
            
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f)
        except Exception as e:
            print(f"Error marking anomaly: {str(e)}")