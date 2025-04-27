import pandas as pd
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker()
services = ["web-server", "database", "auth-service", "payment-service"]
error_codes = ["HTTP_503", "DB_CONN_TIMEOUT", "DEADLOCK", "PAYMENT_GATEWAY_TIMEOUT", ""]
actions = ["blocked", ""]

def generate_log_entry(timestamp):
    service = random.choice(services)
    level = "INFO" if random.random() > 0.2 else random.choice(["ERROR", "WARNING", "CRITICAL"])
    
    log = {
        "timestamp": timestamp.isoformat() + "Z",
        "level": level,
        "service": service,
        "message": "",
        "response_time": f"{random.randint(50, 200)}ms" if service == "web-server" else "",
        "client_ip": fake.ipv4() if service in ["web-server", "auth-service"] else "",
        "error_code": random.choice(error_codes) if level in ["ERROR", "FATAL"] else "",
        "execution_time": f"{random.randint(30, 1500)}ms" if service == "database" else "",
        "query_type": random.choice(["read", "write"]) if service == "database" else "",
        "cpu_usage": random.randint(1, 99) if level == "CRITICAL" else "",
        "memory_usage": f"{random.randint(1, 99)}%" if level == "CRITICAL" else "",
        "affected_tables": "orders;users" if random.random() > 0.8 else "",
        "action": random.choice(actions) if service == "auth-service" else ""
    }
    
    # Custom messages based on service/level
    if service == "web-server":
        log["message"] = f"GET {fake.uri_path()} OK - 200" if level == "INFO" else f"GET {fake.uri_path()} FAILED - {random.choice([500, 503])}"
    elif service == "database":
        log["message"] = f"Query {'SUCCESS' if level == 'INFO' else 'FAILED'}: SELECT * FROM {fake.word()}"
    elif service == "auth-service":
        log["message"] = f"User login: {fake.user_name()}" if level == "INFO" else f"SQL injection attempt detected: {fake.sentence()}"
    
    return log

# Generate 10,000 logs over 24 hours
start_time = datetime(2024, 2, 15, 8, 0, 0)
logs = [generate_log_entry(start_time + timedelta(seconds=5*i)) for i in range(10000)]

df = pd.DataFrame(logs)
df.to_csv("large_logs.csv", index=False)