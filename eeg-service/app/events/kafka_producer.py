from confluent_kafka import Producer
import os, json, logging

from app.events.kafka_config import get_kafka_config

producer = Producer(get_kafka_config())

def send_processed_eeg_event(user_id: int, processed_data: list):
    """
    Publishes processed EEG metrics to the 'eeg.processed.data' Kafka topic.
    """
    topic = "eeg.processed.data"
    payload = {
        "user_id": user_id,
        "records": processed_data
    }
    value = json.dumps(payload)

    try:
        producer.produce(topic=topic, value=value)
        producer.flush()
        logging.info(f"📤 Published processed EEG data for user {user_id} → {topic}")
    except Exception as e:
        logging.exception(f"❌ Failed to publish processed EEG data for user {user_id}: {e}")
