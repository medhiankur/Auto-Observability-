import asyncio
import argparse
from main import log_reader, anomaly_detector, remediator, auto_scaler, process_anomalies

async def run_analysis():
    """Run a complete analysis cycle"""
    print("Reading logs...")
    new_logs = log_reader.read_new_logs()
    
    if not new_logs:
        print("No new logs found.")
        return
        
    print(f"Found {len(new_logs)} new log entries")
    
    print("\nDetecting anomalies...")
    anomalies = anomaly_detector.detect(new_logs)
    
    if not anomalies:
        print("No anomalies detected.")
        return
        
    print(f"Detected {len(anomalies)} anomalies")
    
    print("\nProcessing anomalies...")
    await process_anomalies(anomalies)
    
    print("\nCurrent service scaling status:")
    print(auto_scaler.get_service_status())

def main():
    parser = argparse.ArgumentParser(description="Local runner for Observability Platform")
    parser.add_argument("--analyze", action="store_true", help="Run log analysis")
    parser.add_argument("--reset-scaling", action="store_true", help="Reset service scaling state")
    parser.add_argument("--show-history", action="store_true", help="Show remediation history")
    
    args = parser.parse_args()
    
    if args.reset_scaling:
        auto_scaler.reset_scaling()
        print("Scaling state reset successfully")
        
    if args.show_history:
        history = remediator.get_history()
        print("\nRemediation History:")
        for item in history:
            print(f"\nTimestamp: {item['anomaly'].get('timestamp')}")
            print(f"Service: {item['anomaly'].get('service')}")
            print(f"Status: {item['status']}")
            print(f"Action: {item['suggested_action']}")
            
    if args.analyze:
        asyncio.run(run_analysis())
        
    if not any([args.analyze, args.reset_scaling, args.show_history]):
        parser.print_help()

if __name__ == "__main__":
    main()