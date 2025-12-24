from confluent_kafka import Producer, KafkaException
from app.events.kafka_config import get_kafka_config
import os, json
import logging

logger = logging.getLogger("kafka.producer")

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

logger.info(f"Initializing Kafka producer with broker: {KAFKA_BROKER}")
producer = Producer(get_kafka_config())

def delivery_callback(err, msg):
    """Callback to log Kafka delivery success/failure"""
    if err:
        logger.error(f"❌ Kafka delivery failed: {err}")
    else:
        logger.debug(f"✅ Kafka message delivered to {msg.topic()} [partition {msg.partition()}]")

def send_eeg_event(user_id:str, eeg_payload: dict):
    topic = "eeg.raw.data"
    try:
        value = json.dumps({
            "user_id": user_id,
            "data" : eeg_payload
        })
        producer.produce(topic=topic, value=value, callback=delivery_callback)
        producer.flush(timeout=5.0)
        logger.info(f"✅ Sent EEG event for user {user_id} to topic '{topic}'")
    except KafkaException as e:
        logger.error(f"❌ Failed to send EEG event for user {user_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error sending EEG event: {e}")
        raise