import boto3, json, datetime, os

s3 = boto3.client("s3")

RAW_BUCKET = os.getenv("RAW_EEG_BUCKET")  # add in env & terraform

def save_raw_eeg_to_s3(user_id, eeg_payload):
    ts = datetime.datetime.utcnow().isoformat()
    
    key = f"raw/user-{user_id}/{ts}.json"

    body = json.dumps({
        "user_id": user_id,
        "timestamp": ts,
        "raw": eeg_payload
    })

    s3.put_object(
        Bucket=RAW_BUCKET,
        Key=key,
        Body=body,
        ContentType="application/json"
    )
