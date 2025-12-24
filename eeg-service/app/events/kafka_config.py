import os
from aws_msk_iam_sasl_signer import MSKAuthTokenProvider

def get_kafka_config(is_consumer=False):
    """
    Dynamically loads Kafka configuration depending on environment.
    Works both locally (PLAINTEXT) and on AWS ECS (IAM SASL_SSL).
    """

    app_env = os.getenv("APP_ENV", "local").lower()
    broker = os.getenv("KAFKA_BROKER", "kafka:9092")

    if app_env in ("production", "staging"):
        # AWS MSK (Serverless) with IAM authentication
        def auth_callback(config_str):
            """
            AWS MSK IAM authentication callback
            """
            auth_token, expiry_ms = MSKAuthTokenProvider.generate_auth_token(
                region=os.getenv("KAFKA_REGION", os.getenv("AWS_DEFAULT_REGION", "ap-south-1"))
            )
            return auth_token, expiry_ms / 1000.0

        config = {
            "bootstrap.servers": broker,
            "security.protocol": "SASL_SSL",
            "sasl.mechanism": "OAUTHBEARER",
            "oauth_cb": auth_callback,
            "ssl.ca.location": "/etc/ssl/certs/ca-certificates.crt",
            "enable.idempotence": True,
        }

        if is_consumer:
            config.update({
                "group.id": os.getenv("KAFKA_GROUP_ID", "default-group"),
                "auto.offset.reset": "earliest",
            })

        return config

    # Local (Docker Compose)
    config = {
        "bootstrap.servers": broker,
        "security.protocol": "PLAINTEXT",
    }

    if is_consumer:
        config.update({
            "group.id": os.getenv("KAFKA_GROUP_ID", "default-group"),
            "auto.offset.reset": "earliest",
        })

    return config
