from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send
from typing import Dict, List, Callable
import asyncio
import traceback
from datetime import datetime
import math
import os
import json
import pandas as pd  # Add pandas import

from agents.log_reader import LogReader
from agents.anomaly_detector import AnomalyDetector
from agents.remediator import RemediationAgent
from agents.auto_scaler import AutoScaler
from agents.utils import call_openai

# Load environment variables
load_dotenv()

app = FastAPI(title="Intelligent Observability Platform")

# CORS middleware must be added immediately after app creation
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
  GZipMiddleware,
  minimum_size=1000
)

LLM_RESPONSES_FILE = os.path.join("state", "llm_responses.json")

def load_llm_responses():
    if os.path.exists(LLM_RESPONSES_FILE):
        with open(LLM_RESPONSES_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_llm_response(entry):
    responses = load_llm_responses()
    responses.append(entry)
    with open(LLM_RESPONSES_FILE, "w") as f:
        json.dump(responses, f, indent=2)

# Initialize agents
log_reader = LogReader("./logs")
anomaly_detector = AnomalyDetector()
remediator = RemediationAgent()
auto_scaler = AutoScaler()

# Load LLM responses from file
llm_responses = load_llm_responses()

# Mock remediation history for demo/testing
mock_remediation_history = [
    {
        "action": "Scale up web-server",
        "status": "success",
        "timestamp": "2025-04-16T10:01:00Z"
    },
    {
        "action": "Restart database node",
        "status": "success",
        "timestamp": "2025-04-16T10:06:00Z"
    }
]

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for better error messages"""
    error_msg = str(exc)
    print(f"Global exception handler caught: {error_msg}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": error_msg,
            "path": request.url.path
        }
    )

async def process_anomalies(anomalies: List[Dict]):
    """Process detected anomalies in the background, including LLM call."""
    import asyncio
    for anomaly in anomalies:
        try:
            print(f"Processing anomaly: {anomaly}")
            # Get remediation suggestions
            remediation = await remediator.suggest_remediation(anomaly)
            print(f"Remediation suggestion: {remediation}")
            
            # Enhanced prompt for code-focused remediation
            prompt = f"""Please provide a detailed remediation solution with code examples for this issue:
Issue Type: {anomaly.get('type', 'anomaly')}
Service: {anomaly.get('service', 'unknown service')}
Message: {anomaly.get('message', '')}

Include in your response:
1. Brief explanation of the issue
2. Code snippets or commands to resolve the problem
3. Configuration changes needed (if any)
4. Verification steps with code examples"""

            # Call LLM
            loop = asyncio.get_event_loop()
            llm_response = await loop.run_in_executor(None, call_openai, prompt)
            print(f"LLM response: {llm_response}")
            
            # Store LLM response
            llm_entry = {
                "timestamp": anomaly.get("timestamp"),
                "query": prompt,
                "response": llm_response
            }
            llm_responses.append(llm_entry)
            print(f"Appending LLM entry: {llm_entry}")
            save_llm_response(llm_entry)
            print(f"Saved LLM entry to file.")
            
            # Evaluate scaling actions
            scaling_actions = auto_scaler.evaluate_scaling([anomaly])
            if scaling_actions:
                remediation["scaling_actions"] = scaling_actions
        except Exception as e:
            print(f"Error processing anomaly: {str(e)}")
            print(traceback.format_exc())

@app.get("/")
async def root():
    return {"status": "running", "service": "Intelligent Observability Platform"}

@app.get("/logs/recent")
async def get_recent_logs(minutes: int = 5):
    """Get logs from the last N minutes"""
    return log_reader.get_recent_logs(minutes)

@app.post("/analyze")
async def analyze_logs(background_tasks: BackgroundTasks):
    """Analyze new logs for anomalies"""
    try:
        # Read new logs
        new_logs = log_reader.read_new_logs()
        
        if not new_logs:
            return {"message": "No new logs to analyze"}
        
        # Detect anomalies
        anomalies = anomaly_detector.detect(new_logs)
        
        if anomalies:
            # Process anomalies in the background
            background_tasks.add_task(process_anomalies, anomalies)
            
        return {
            "logs_analyzed": len(new_logs),
            "anomalies_detected": len(anomalies),
            "anomalies": clean_json(anomalies)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/remediation/history")
async def get_remediation_history():
    """Get history of remediation actions"""
    return remediator.get_history()

@app.get("/scaling/status")
async def get_scaling_status():
    """Get current scaling status of services"""
    return auto_scaler.get_service_status()

@app.post("/scaling/reset")
async def reset_scaling():
    """Reset service scaling to initial state"""
    auto_scaler.reset_scaling()
    return {"message": "Scaling state reset successfully"}

def clean_json(obj):
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_json(v) for v in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif hasattr(obj, 'isoformat'):  # Handle any datetime-like object
        return obj.isoformat()
    else:
        return obj

@app.get("/api/anomalies")
async def get_anomalies():
    """Get recent anomalies with better error handling"""
    try:
        # Get logs from the last 10 minutes of available data
        recent_logs = log_reader.get_recent_logs(10)
        
        if not recent_logs:
            print("No recent logs found")
            return []
        
        print(f"Found {len(recent_logs)} recent logs")
        
        # Convert timestamps to proper format
        for log in recent_logs:
            if isinstance(log.get("timestamp"), str):
                try:
                    log["timestamp"] = datetime.fromisoformat(log["timestamp"].replace('Z', '+00:00'))
                except ValueError as e:
                    print(f"Error parsing timestamp: {e}")
                    log["timestamp"] = datetime.now()  # Fallback to current time
        
        # Detect anomalies
        anomalies = anomaly_detector.detect(recent_logs)
        print(f"Detected {len(anomalies)} anomalies")
        
        # Prepare anomalies for JSON serialization
        formatted_anomalies = []
        for anomaly in anomalies:
            formatted_anomaly = anomaly.copy()
            if isinstance(formatted_anomaly.get("timestamp"), datetime):
                formatted_anomaly["timestamp"] = formatted_anomaly["timestamp"].isoformat()
            formatted_anomalies.append(formatted_anomaly)
        
        # Clean anomalies for JSON
        cleaned_anomalies = [clean_json(anomaly) for anomaly in formatted_anomalies]
        
        return cleaned_anomalies
        
    except Exception as e:
        print(f"Error in /api/anomalies: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Error detecting anomalies",
                "error": str(e),
                "type": type(e).__name__
            }
        )

@app.get("/api/scaling")
async def get_scaling():
    """Get current scaling status"""
    try:
        return auto_scaler.get_service_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/remediation")
async def get_remediation():
    # Return mock data for demo/testing
    return mock_remediation_history

@app.get("/api/llm-responses")
async def get_llm_responses():
    return llm_responses

@app.get("/api/llm-response")
async def get_llm_response(prompt: str = Query(...)):
    """Get a real-time LLM response from OpenAI GPT-3.5-turbo using the .env key."""
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_openai, prompt)
        return {"prompt": prompt, "response": response}
    except Exception as e:
        return {"prompt": prompt, "response": None, "error": str(e)}

@app.post("/api/llm-sample-response")
async def llm_sample_response():
    """Send a sample prompt to OpenAI LLM, store and return the response for the frontend."""
    prompt = "How do I remediate a database deadlock?"
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_openai, prompt)
        llm_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": prompt,
            "response": response
        }
        llm_responses.append(llm_entry)
        save_llm_response(llm_entry)
        return llm_entry
    except Exception as e:
        return {"query": prompt, "response": None, "error": str(e)}

@app.post("/api/llm-force-sample")
async def llm_force_sample():
    """Force a sample LLM response to be saved to state/llm_responses.json for frontend testing."""
    prompt = "What is the capital of France?"
    try:
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, call_openai, prompt)
        llm_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": prompt,
            "response": response
        }
        llm_responses.append(llm_entry)
        save_llm_response(llm_entry)
        return llm_entry
    except Exception as e:
        return {"query": prompt, "response": None, "error": str(e)}

@app.post("/api/llm-anomaly-sample")
async def llm_anomaly_sample():
    """Process 1 sample anomaly with careful timestamp handling"""
    print("Starting anomaly detection...")
    recent_logs = log_reader.get_recent_logs(10)
    if not recent_logs:
        return {"message": "No anomalies detected in recent logs."}
        
    # Convert timestamps in logs
    for log in recent_logs:
        if isinstance(log.get("timestamp"), (datetime, pd.Timestamp)):
            log["timestamp"] = log["timestamp"].isoformat()
            
    print(f"Processing {len(recent_logs)} logs...")
    anomalies = anomaly_detector.detect(recent_logs)
    if not anomalies:
        return {"message": "No anomalies detected in logs"}
        
    # Get first anomaly and ensure all nested timestamps are converted
    sample_anomaly = clean_json(anomalies[0])
    
    # Create prompt that asks for code snippets
    prompt = f"""Please provide a remediation solution with code examples for this issue:
Issue Type: {sample_anomaly.get('type', 'unknown issue')}
Service: {sample_anomaly.get('service', 'service')}
Message: {sample_anomaly.get('message', '')}

Include in your response:
1. Brief explanation of the issue
2. Code snippets or commands to fix the problem
3. Any configuration changes needed"""
    
    print(f"Sending prompt to LLM: {prompt}")
    
    try:
        # Send to LLM
        response = call_openai(prompt)
        print(f"Received LLM response: {response}")
        
        # Create entry with current timestamp
        llm_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": prompt,
            "response": response,
            "anomaly": sample_anomaly
        }
        
        # Save response
        print("Saving to llm_responses.json...")
        os.makedirs("state", exist_ok=True)
        llm_responses.append(llm_entry)
        save_llm_response(llm_entry)
        print("Response saved successfully")
        
        return {"status": "success", "llm_entry": llm_entry}
        
    except Exception as e:
        print(f"Error processing anomaly: {str(e)}")
        return {"status": "error", "message": str(e)}

@app.post("/api/process-first-anomaly")
async def process_first_anomaly():
    """Process only the first detected anomaly and ensure LLM response is saved."""
    try:
        print("Starting anomaly detection...")
        recent_logs = log_reader.get_recent_logs(10)
        if not recent_logs:
            print("No logs found")
            return {"status": "error", "message": "No logs found"}

        print(f"Found {len(recent_logs)} logs, detecting anomalies...")
        anomalies = anomaly_detector.detect(recent_logs)
        if not anomalies:
            print("No anomalies detected")
            return {"status": "error", "message": "No anomalies detected"}

        print(f"Detected {len(anomalies)} anomalies, processing first one...")
        first_anomaly = anomalies[0]
        if isinstance(first_anomaly.get("timestamp"), datetime):
            first_anomaly["timestamp"] = first_anomaly["timestamp"].isoformat()
        
        # Create code-focused prompt
        prompt = f"""Please provide a detailed remediation solution with code examples for this issue:
Issue Type: {first_anomaly.get('type', 'unknown')}
Service: {first_anomaly.get('service', 'unknown')}
Message: {first_anomaly.get('message', '')}

Include in your response:
1. Brief explanation of the issue
2. Code snippets or commands to fix the problem
3. Configuration changes needed (if any)
4. Verification steps with code examples
5. Rollback steps if needed"""

        print(f"Sending prompt to LLM: {prompt}")

        # Call LLM
        try:
            response = call_openai(prompt)
            print(f"Received LLM response: {response}")
            
            # Create and save entry
            llm_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "query": prompt,
                "response": response,
                "anomaly_details": clean_json(first_anomaly)
            }
            
            print("Saving response to llm_responses.json...")
            os.makedirs("state", exist_ok=True)
            llm_responses.append(llm_entry)
            save_llm_response(llm_entry)
            print("Response saved successfully")
            
            return {
                "status": "success",
                "anomaly": clean_json(first_anomaly),
                "llm_response": llm_entry
            }
        except Exception as e:
            print(f"Error calling LLM: {str(e)}")
            return {"status": "error", "message": f"LLM error: {str(e)}"}
            
    except Exception as e:
        print(f"Error in process_first_anomaly: {str(e)}")
        print(traceback.format_exc())
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="debug")
