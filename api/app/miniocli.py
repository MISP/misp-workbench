import os
from minio import Minio

MinioClient = Minio(
    os.environ["MINIO_HOST"],
    access_key=os.environ["MINIO_ROOT_USER"],
    secret_key=os.environ["MINIO_ROOT_PASSWORD"],
    secure=False,
)

found = MinioClient.bucket_exists(os.environ["MINIO_BUCKET"])
if not found:
    MinioClient.make_bucket(os.environ["MINIO_BUCKET"])
