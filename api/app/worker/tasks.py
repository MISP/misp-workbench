import logging
import os
import smtplib

from app.database import SessionLocal
from app.repositories import events as events_repository
from app.repositories import servers as servers_repository
from app.repositories import users as users_repository
from app.settings import get_settings
from celery import Celery

# Celery configuration
app = Celery()
app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND"),
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

logger = logging.getLogger(__name__)

db = SessionLocal()


@app.task
def server_pull_by_id(server_id: int, user_id: int, technique: str):
    logger.info("pull server_id=%s job started", server_id)

    user = users_repository.get_user_by_id(db, user_id)
    if user is None:
        raise Exception("User not found")

    servers_repository.pull_server_by_id(db, get_settings(), server_id, user, technique)
    logger.info("pull server_id=%s job finished", server_id)

    return True


@app.task
def handle_created_attribute(attribute_id: int, event_id: int):
    logger.info("handling created attribute id=%s job started", attribute_id)

    events_repository.increment_attribute_count(db, event_id)

    return True


@app.task
def handle_deleted_attribute(attribute_id: int, event_id: int):
    logger.info("handling deleted attribute id=%s job started", attribute_id)

    events_repository.decrement_attribute_count(db, event_id)

    return True


@app.task
def send_email(email: dict):
    logger.info("sending email job started")

    sender = f'<{email["from"]}>'
    receiver = f'<{email["to"]}>'

    message = f"""\
    Subject: {email["subject"]}
    To: {receiver}
    From: {sender}

    {email["body"]}"""

    with smtplib.SMTP(
        os.environ.get("MAIL_SERVER"), os.environ.get("MAIL_PORT")
    ) as server:
        server.login(os.environ.get("MAIL_USERNAME"), os.environ.get("MAIL_PASSWORD"))
        server.sendmail(sender, receiver, message)

    return True
