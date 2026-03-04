import boto3
from app.settings import get_settings


Settings = get_settings()

if Settings.Storage.engine == "s3":
    s = Settings.Storage.s3
    S3Client = boto3.client(
        "s3",
        endpoint_url=f"{'https' if s.secure else 'http'}://{s.endpoint}",
        aws_access_key_id=s.access_key,
        aws_secret_access_key=s.secret_key,
        region_name="garage",
    )

else:
    S3Client = None
