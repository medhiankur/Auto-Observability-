from typing import Dict, List
import json
from pathlib import Path

class AutoScaler:
    def __init__(self, config_path: str = "./config"):
        self.config_path = Path(config_path)
        self.config_path.mkdir(exist_ok=True)
        self.state_file = self.config_path / "scaling_state.json"
        self._initialize_state()
        
    def _initialize_state(self):
        """Initialize or load scaling state"""
        if not self.state_file.exists():
            initial_state = {
                "services": {
                    "web-server": {"instances": 1, "max_instances": 5},
                    "database": {"instances": 1, "max_instances": 3},
                    "auth-service": {"instances": 1, "max_instances": 3},
                    "payment-service": {"instances": 1, "max_instances": 3}
                }
            }
            with open(self.state_file, 'w') as f:
                json.dump(initial_state, f, indent=2)
        
    def evaluate_scaling(self, anomalies: List[Dict]) -> List[Dict]:
        """Evaluate scaling decisions based on anomalies"""
        scaling_actions = []
        
        with open(self.state_file, 'r') as f:
            state = json.load(f)
        
        for anomaly in anomalies:
            service = anomaly.get('service')
            if not service or service not in state['services']:
                continue
                
            service_state = state['services'][service]
            current_instances = service_state['instances']
            max_instances = service_state['max_instances']
            
            # Scale up on high CPU/memory usage or response time issues
            should_scale = (
                anomaly.get('cpu_usage', 0) > 80 or
                (anomaly.get('memory_usage', '0%').rstrip('%')) > '80' or
                (anomaly.get('response_time', '0').rstrip('ms')) > '1000'
            )
            
            if should_scale and current_instances < max_instances:
                service_state['instances'] += 1
                scaling_actions.append({
                    'service': service,
                    'action': 'scale_up',
                    'from_instances': current_instances,
                    'to_instances': current_instances + 1,
                    'reason': 'High resource usage or response time'
                })
        
        # Save updated state
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
            
        return scaling_actions
    
    def get_service_status(self) -> Dict:
        """Get current scaling status of all services"""
        with open(self.state_file, 'r') as f:
            state = json.load(f)
        
        # Transform the data into the format expected by frontend
        formatted_status = {}
        for service, info in state['services'].items():
            formatted_status[service] = {
                'current_instances': info['instances'],
                'min_instances': 1,  # Default minimum
                'max_instances': info['max_instances']
            }
        return formatted_status
    
    def reset_scaling(self):
        """Reset all services to initial state"""
        self._initialize_state()