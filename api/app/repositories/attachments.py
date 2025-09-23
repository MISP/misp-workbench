import time
import logging
import hashlib
import io
import os


from fastapi.responses import StreamingResponse
from app.services.minio import get_minio_client
from app.services.attachments import get_attachment, get_attachment_template
from starlette import status
import app.schemas.event as event_schemas
from app.schemas import object as object_schemas
import app.schemas.attribute as attribute_schemas
from app.repositories import objects as objects_repository
from app.repositories import attributes as attributes_repository
from sqlalchemy.orm import Session
from app.settings import Settings, get_settings
from fastapi import (
    HTTPException,
    UploadFile,
)

logger = logging.getLogger(__name__)


def store_attachment(
    file_content,
    filename: str | None = None,
    settings: Settings = get_settings(),
) -> str:
    try:
        # upload file to minio
        if settings.Storage.engine == "minio":
            MinioClient = get_minio_client()
            MinioClient.put_object(
                settings.Storage.minio.bucket,
                filename,
                io.BytesIO(file_content),
                length=len(file_content),
                part_size=10 * 1024 * 1024,
            )

        # upload file to local storage
        if settings.Storage.engine == "local":
            if os.path.exists("/tmp/attachments") is False:
                os.makedirs("/tmp/attachments")

            with open(f"/tmp/attachments/{filename}", "wb") as f:
                f.write(file_content)
    except Exception as e:
        logger.error(f"Error storing attachment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error storing attachment",
        )


def upload_attachments_to_event(
    db: Session,
    event: event_schemas.Event,
    attachments: list[UploadFile],
    attachments_meta: dict = None,
) -> list[object_schemas.Object]:

    file_objects = []

    try:
        for attachment in attachments:

            attachment_meta = attachments_meta.get(attachment.filename)
            template = get_attachment_template()

            file_object = object_schemas.ObjectCreate(
                name="file",
                template_uuid=template["uuid"],
                meta_category=template["meta_category"],
                template_version=template["version"],
                comment=attachment.filename,
                event_id=event.id,
                timestamp=int(time.time()),
            )

            filename_attribute = attribute_schemas.AttributeCreate(
                event_id=event.id,
                object_relation="filename",
                category=attachment_meta.get("category", "External analysis"),
                type="filename",
                value=attachment.filename,
                timestamp=int(time.time()),
                distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
            )
            file_object.attributes.append(filename_attribute)

            # read file content
            file_content = attachment.file.read()

            # get file sha1
            sha1 = hashlib.sha1()
            sha1.update(file_content)
            sha1 = sha1.hexdigest()
            sha1_attribute = attribute_schemas.AttributeCreate(
                event_id=event.id,
                object_relation="sha1",
                category="External analysis",
                type="sha1",
                value=sha1,
                timestamp=int(time.time()),
                distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
            )
            file_object.attributes.append(sha1_attribute)

            # get file sha256
            sha256 = hashlib.sha256()
            sha256.update(file_content)
            sha256 = sha256.hexdigest()
            sha256_attribute = attribute_schemas.AttributeCreate(
                event_id=event.id,
                object_relation="sha256",
                category="External analysis",
                type="sha256",
                value=sha256,
                timestamp=int(time.time()),
                distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
            )
            file_object.attributes.append(sha256_attribute)

            # get file md5
            md5sum = hashlib.md5(file_content).hexdigest()
            md5_attribute = attribute_schemas.AttributeCreate(
                event_id=event.id,
                object_relation="md5",
                category="External analysis",
                type="md5",
                value=md5sum,
                timestamp=int(time.time()),
                distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
            )
            file_object.attributes.append(md5_attribute)

            # get file size
            size = len(file_content)
            size_attribute = attribute_schemas.AttributeCreate(
                event_id=event.id,
                object_relation="size-in-bytes",
                category="Other",
                type="size-in-bytes",
                value=str(size),
                timestamp=int(time.time()),
                distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
            )
            file_object.attributes.append(size_attribute)

            # attachment attribute
            attachment_attribute = attribute_schemas.AttributeCreate(
                event_id=event.id,
                object_relation="attachment",
                category="Payload delivery",
                type="attachment",
                value=attachment.filename,
                timestamp=int(time.time()),
                distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
            )
            file_object.attributes.append(attachment_attribute)

            # malware analysis
            if attachment_meta.get("is_malware", False):
                malware_attribute = attribute_schemas.AttributeCreate(
                    event_id=event.id,
                    object_relation="malware",
                    category="External analysis",
                    type="malware",
                    value="true",
                    timestamp=int(time.time()),
                    distribution=event_schemas.DistributionLevel.INHERIT_EVENT,
                )
                file_object.attributes.append(malware_attribute)

            db_file_object = objects_repository.create_object(db, file_object)
            attachment_attribute_db = [
                db_file_object_attr
                for db_file_object_attr in db_file_object.attributes
                if db_file_object_attr.type == "attachment"
            ][0]

            store_attachment(file_content, attachment_attribute_db.uuid)

            file_objects.append(db_file_object)

        return file_objects

    except Exception as e:
        logger.error(f"Error uploading attachment for event: {event.uuid}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading attachment",
        )


def download_attachment(
    db: Session,
    attachment_uuid: str,
    settings: Settings = get_settings(),
) -> StreamingResponse:

    db_attribute = attributes_repository.get_attribute_by_uuid(db, attachment_uuid)

    try:
        return StreamingResponse(
            io.BytesIO(get_attachment(attachment_uuid, settings)),
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f'attachment; filename="{db_attribute.value or attachment_uuid}"'
            },
        )

    except Exception as e:
        logger.error(f"Error fetching attachment: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching attachment",
        )
