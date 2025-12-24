from confluent_kafka import Consumer
import os, json, logging, threading, asyncio
from app.events.kafka_config import get_kafka_config

KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

conf = get_kafka_config(is_consumer=True)
conf["group.id"] = "gateway-consumer"

consumer = Consumer(conf)
consumer.subscribe(["eeg.processed.data"])

# Store reference to the event loop
main_loop = None

def set_event_loop(loop):
    """Set the main event loop for async operations."""
    global main_loop
    main_loop = loop

def _get_label(value, metric_type):
    """Convert numeric value to label."""
    if value is None:
        return "Unknown"
    
    if metric_type == "focus":
        if value >= 2.5:
            return "High"
        elif value >= 1.5:
            return "Medium"
        else:
            return "Low"
    elif metric_type == "stress":
        if value >= 2.5:
            return "High"
        elif value >= 1.5:
            return "Medium"
        else:
            return "Low"
    else:  # wellness
        if value >= 70:
            return "Good"
        elif value >= 40:
            return "Fair"
        else:
            return "Poor"

async def broadcast_metrics(data: dict):
    """Broadcast processed metrics to WebSocket clients."""
    from app.websocket.metrics_manager import metrics_manager
    
    try:
        user_id = str(data.get("user_id"))  # Convert to string for consistency
        records = data.get("records", [])
        
        if not user_id or not records:
            logging.warning(f"⚠️ Skipping broadcast - user_id: {user_id}, records: {len(records) if records else 0}")
            return
        
        # Get latest metrics from the records
        latest = records[-1]  # Last record has most recent data
        
        # Log the structure to debug
        logging.info(f"🔍 Latest record keys: {list(latest.keys())}")
        
        metrics_message = {
            "type": "PROCESSED_METRICS",
            "user_id": user_id,
            "timestamp": latest.get("timestamp"),
            "metrics": {
                "focus": {
                    "value": latest.get("focus_label"),  # Named _label but contains value
                    "label": _get_label(latest.get("focus_label"), "focus")
                },
                "stress": {
                    "value": latest.get("stress_label"),  # Named _label but contains value
                    "label": _get_label(latest.get("stress_label"), "stress")
                },
                "wellness": {
                    "value": latest.get("wellness_label"),  # Named _label but contains value
                    "label": _get_label(latest.get("wellness_label"), "wellness")
                }
            }
        }
        
        await metrics_manager.send_to_user(user_id, metrics_message)
        logging.info(f"📊 Sent metrics to user {user_id}: Focus={latest.get('focus_label'):.2f}, Stress={latest.get('stress_label'):.2f}")
        
    except Exception as e:
        logging.error(f"❌ Error broadcasting metrics: {e}", exc_info=True)

def handle_processed_metrics(data: dict):
    """Handle processed metrics received from Kafka."""
    try:
        user_id = str(data.get("user_id"))  # Convert to string for consistency
        records = data.get("records", [])
        
        logging.info(f"🎯 Gateway consuming processed metrics for user {user_id}: {len(records)} records")
        
        # Broadcast to WebSocket clients
        if main_loop and not main_loop.is_closed():
            asyncio.run_coroutine_threadsafe(broadcast_metrics(data), main_loop)
    
    except Exception as e:
        logging.error(f"❌ Error handling processed metrics: {e}", exc_info=True)

def consume_loop():
    """Kafka consumer loop."""
    logging.info("👂 Gateway consuming 'eeg.processed.data' topic")
    while True:
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            logging.error(f"Kafka error: {msg.error()}")
            continue
        
        data = json.loads(msg.value().decode("utf-8"))
        handle_processed_metrics(data)

def start_consumer():
    """Start consumer in background thread."""
    thread = threading.Thread(target=consume_loop, daemon=True)
    thread.start()
    logging.info("✅ Gateway Kafka consumer started")
