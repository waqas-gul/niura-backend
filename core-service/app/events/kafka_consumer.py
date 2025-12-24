from confluent_kafka import Consumer
import os, json, logging, threading
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.eeg_record import EEGRecord
from datetime import datetime
from app.events.kafka_config import get_kafka_config

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

conf = get_kafka_config(is_consumer=True)
conf["group.id"] = "core-service-consumer"

consumer = Consumer(conf)
consumer.subscribe(["eeg.processed.data"])

def handle_processed_eeg(data: dict):
    """Handle processed EEG data received from Kafka and save it in core_db."""
    try:
        user_id = int(data.get("user_id"))
        records = data.get("records", [])
        logging.info(f"📥 Received processed EEG data for user {user_id}: {len(records)} records")

        if not records:
            logging.warning(f"⚠️ No records found in EEG payload for user {user_id}")
            return

        db: Session = SessionLocal()
        eeg_db_records = []

        for rec in records:
            eeg = EEGRecord(
                user_id=user_id,
                timestamp=datetime.fromisoformat(rec["timestamp"]),
                focus_label=float(rec["focus_label"]),
                stress_label=float(rec["stress_label"]),
                wellness_label=float(rec["wellness_label"]),
                created_at=datetime.utcnow(),
                created_by=user_id,
                updated_at=datetime.utcnow(),
                updated_by=user_id,
            )
            eeg_db_records.append(eeg)

        db.add_all(eeg_db_records)
        db.commit()
        db.close()

        logging.info(f"✅ Saved {len(eeg_db_records)} EEG records for user {user_id} in core_db")

    except Exception as e:
        logging.exception(f"❌ Error while saving processed EEG data: {str(e)}")


def consume_loop():
    logging.info("👂 Core-service consuming topic 'eeg.processed.data'")
    while True:
        try:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logging.error(f"Kafka error: {msg.error()}")
                continue
            data = json.loads(msg.value().decode("utf-8"))
            handle_processed_eeg(data)
        except Exception as e:
            logging.exception(f"Error in consume_loop: {e}")


def start_consumer():
    """Start Kafka consumer in a background thread."""
    logging.info("🚀 Starting Core-service Kafka consumer...")
    t = threading.Thread(target=consume_loop, daemon=True)
    t.start()
