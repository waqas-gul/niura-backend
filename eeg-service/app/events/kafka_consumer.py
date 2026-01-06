import sys
from confluent_kafka import Consumer
import os, json, threading, logging, requests
from app.events.kafka_config import get_kafka_config
from app.utils.s3_raw_backup import save_raw_eeg_to_s3


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
    force=True  # <-- overrides uvicorn's root handlers
)

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")
# Use FFT endpoint for faster processing (can switch back to /bulk for BrainFlow)
EEG_API_URL=os.getenv("EEG_API_URL", "http://localhost:8002/api/bulk-fft")


conf = get_kafka_config(is_consumer=True)
conf["group.id"] = "eeg-service-consumer"

consumer = Consumer(conf)
consumer.subscribe(["eeg.raw.data"])

def consume_loop():
    logging.info("👂 EEG-service consuming 'eeg.raw.data'")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logging.error(f"Kafka error: {msg.error()}")
            continue
        data = json.loads(msg.value().decode("utf-8"))
        handle_eeg_data(data)

def handle_eeg_data(data):
    """Forward EEG Kafka message to the /bulk endpoint."""
    try:
        logging.info(f"📩 EEG message received for user {data.get('user_id')}")
        user_id=data.get("user_id")
        eeg_payload = data.get("data", {})
        

        save_raw_eeg_to_s3(user_id, eeg_payload) 
        # Send it to your FastAPI endpoint
        response = requests.post(
            EEG_API_URL,
            json={"batch": {**eeg_payload, "user_id": user_id}},  # ✅ merged inside
            timeout=10,
)


       # ✅ Print both status and the returned message
        if response.status_code == 200:
            try:
                result = response.json()
                logging.info(f"✅ EEG data forwarded successfully → {result}")
            except Exception:
                logging.info(f"✅ EEG data forwarded successfully (no JSON body)")
        else:
            logging.warning(
                f"⚠️ Failed to forward EEG data to /bulk: {response.status_code} {response.text}"
            )

        # ✅ Return the actual response content in case other parts need it
        return response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text

    except Exception as e:
        logging.exception(f"❌ Error forwarding EEG data: {e}")
        return None

def start_consumer():
    t = threading.Thread(target=consume_loop, daemon=True)
    t.start()