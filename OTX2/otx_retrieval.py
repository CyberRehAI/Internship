import sys
import logging
from OTXv2 import OTXv2
from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv("OTX_API_KEY")


# Initialize logging for pipeline monitoring
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def retrieve_pulse_data(api_key, pulse_id):
    """Retrieves and logs indicators from a specific OTX Pulse."""
    try:
        # Initialize the OTX connection
        otx = OTXv2(api_key)
        logging.info(f"Authenticating and retrieving indicators for Pulse ID: {pulse_id}")
        
        # Execute data retrieval
        indicators = otx.get_pulse_indicators(pulse_id)
        
        if not indicators:
            logging.warning("No indicators found or Pulse is empty. Check your Pulse ID.")
            return

        for ind in indicators:
            print(f"Indicator: {ind.get('indicator')} | Type: {ind.get('type')}")
            
    except Exception as e:
        # Catch authentication failures, network timeouts, or malformed responses
        logging.error(f"Execution failed. Verify your API Key and network connection. Details: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # In a production environment, load these from secure environment variables.
    if not API_KEY:
        raise ValueError("OTX_API_KEY is missing. Set it in your .env file.")
    TARGET_PULSE = "6a47950711440db76d84e5de"
    retrieve_pulse_data(API_KEY, TARGET_PULSE)