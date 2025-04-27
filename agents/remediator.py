from typing import Dict, List
import json
from pathlib import Path
from .utils import call_openai

class RemediationAgent:
    def __init__(self, state_dir: str = "./state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        self.history_file = self.state_dir / "remediation_history.json"
        self._initialize_history()
    
    def _initialize_history(self):
        """Initialize or load remediation history"""
        if not self.history_file.exists():
            with open(self.history_file, 'w') as f:
                json.dump([], f)
    
    async def suggest_remediation(self, anomaly: Dict) -> Dict:
        """Generate remediation suggestions using Groq LLM"""
        prompt = f"""Given the following system anomaly, suggest specific remediation steps:
        Service: {anomaly['service']}
        Level: {anomaly['level']}
        Message: {anomaly['message']}
        CPU Usage: {anomaly.get('cpu_usage', 'N/A')}
        Memory Usage: {anomaly.get('memory_usage', 'N/A')}
        Response Time: {anomaly.get('response_time', 'N/A')}
        
        Provide specific commands or configuration changes that could resolve the issue.
        """
        
        suggestion = await call_openai(prompt)
        
        remediation = {
            "anomaly": anomaly,
            "suggested_action": suggestion,
            "status": "pending"
        }
        
        # Save to history
        self._save_to_history(remediation)
        
        return remediation
    
    def _save_to_history(self, remediation: Dict):
        """Save remediation action to history"""
        with open(self.history_file, 'r') as f:
            history = json.load(f)
        
        history.append(remediation)
        
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def get_history(self) -> List[Dict]:
        """Get remediation action history"""
        with open(self.history_file, 'r') as f:
            return json.load(f)
    
    def mark_remediation_status(self, anomaly_timestamp: str, status: str):
        """Update the status of a remediation attempt"""
        for item in self.get_history():
            if item["anomaly"].get("timestamp") == anomaly_timestamp:
                item["status"] = status
                self._save_to_history(item)
                break