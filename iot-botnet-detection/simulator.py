import requests
import pandas as pd
import time
import argparse

def run_simulator(api_url, api_key, data_file="test_data.csv", delay=1.0):
    print(f"[*] Starting IoT Telemetry Simulator...")
    print(f"[*] Target API: {api_url}")
    print(f"[*] Data Source: {data_file}")
    
    try:
        df = pd.read_csv(data_file)
        import joblib
        scaler = joblib.load('model/scaler.pkl')
        if len(df.columns) == len(scaler.feature_names_in_):
            df.columns = scaler.feature_names_in_
            print("[*] Successfully attached correct feature names to the telemetry payload!")
    except FileNotFoundError:
        print(f"[!] Error: Could not find {data_file}. Please ensure the file exists.")
        return
    except Exception as e:
        print(f"[!] Warning: Could not load feature names locally: {e}")

    headers = {}
    if api_key:
        headers["x-functions-key"] = api_key
        print("[*] Security: API Key included in headers.")
    else:
        print("[!] Warning: No API key provided. Request may be rejected if endpoint is secured.")

    print("\n" + "="*50)
    for index, row in df.iterrows():
        print(f"[{index}] Sending telemetry packet...")
        
        # Convert row back to CSV format to send as a file attachment
        csv_data = row.to_frame().T.to_csv(index=False)
        files = {"file": ("telemetry.csv", csv_data, "text/csv")}
        
        try:
            start_time = time.time()
            response = requests.post(api_url, files=files, headers=headers)
            rtt = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                print(f"    [+] Success ({rtt}ms) | Response: {response.json()}")
            else:
                print(f"    [-] Failed  ({rtt}ms) | Status Code: {response.status_code} | Error: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"    [!] Connection Error: {e}")
            
        time.sleep(delay)
        
    print("="*50)
    print("[*] Simulation Completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IoT Telemetry Simulator")
    # Default URL is local Azure Functions Core Tools
    parser.add_argument("--url", default="http://localhost:7071/api/predict", help="Azure Function API URL")
    parser.add_argument("--key", default="", help="Azure Function API Key (x-functions-key)")
    parser.add_argument("--file", default="test_data.csv", help="Path to CSV dataset")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests in seconds")
    
    args = parser.parse_args()
    run_simulator(args.url, args.key, args.file, args.delay)
