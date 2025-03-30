from ..intent_exec.env.traffic import start_traffic, end_traffic
from ..utils.export_csv import export_metrics
from .service_monitor import monitor_services
from .data_export import export_service_data_csv, export_with_vpa_comparison
from .data_visualization import create_service_figures
import os
import time

def main():
    # Start the traffic simulation
    process = start_traffic()
    
    try:
        # Run for exactly 4200 seconds (70 minutes)
        total_runtime = 4200
        check_interval = 30  # Check status every 30 seconds
        
        print(f"\nRunning for {total_runtime} seconds, collecting data every {check_interval} seconds...")
        
        # Monitor services and collect data
        timestamps, service_data = monitor_services(total_runtime, check_interval)
        
        print(f"\nCompleted the {total_runtime} second run.")
            
    except KeyboardInterrupt:
        print("\nShutting down due to user interrupt...")
    except Exception as e:
        print(f"\nError occurred: {e}")
    finally:
        # Ensure proper cleanup of the traffic process
        if process:
            end_traffic(process)
            print("Traffic simulation stopped")
            
        # Clean up the VPA YAML file if it exists
        if os.path.exists("vpa.yaml"):
            os.remove("vpa.yaml")
            print("VPA configuration file removed")
    
    # Create and save figures
    create_service_figures(timestamps, service_data)
    
    # Export CSV of service data
    export_service_data_csv(timestamps, service_data)
    
    # Export VPA comparison data
    export_with_vpa_comparison(service_data)
    
    # Export other metrics
    export_metrics()

if __name__ == "__main__":
    main()