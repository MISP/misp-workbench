
from app.settings import Settings, get_settings
from app.services.minio import get_minio_client
from app.services.object_templates import get_local_object_templates
import base64

def get_attachment(
    attachment_uuid: str,
    settings: Settings = get_settings(),
) -> bytes:
    if settings.Storage.engine == "minio":
        MinioClient = get_minio_client()

        data = MinioClient.get_object(settings.Storage.minio.bucket, attachment_uuid)
        return data.read()

    # get attachment from local storage
    if settings.Storage.engine == "local":
        with open(f"/tmp/attachments/{attachment_uuid}", "rb") as f:
            return f.read()
        

def get_b64_attachment(
    attachment_uuid: str,
    settings: Settings = get_settings(),
) -> str:
    file_content = get_attachment(attachment_uuid, settings)
    return base64.b64encode(file_content).decode("utf-8")


def get_attachment_template_uuid() -> str:
    return "688c46fb-5edb-40a3-8273-1af7923e2215"

def get_attachment_template() -> dict:
    object_templates = get_local_object_templates()

    for template in object_templates:
        if template["uuid"] == get_attachment_template_uuid():
            return template


