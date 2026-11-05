import os
import uuid
from datetime import datetime, timezone
from io import BytesIO

import boto3
from botocore.exceptions import ClientError
from botocore.client import Config


MINIO_ENDPOINT = os.getenv(
    "MINIO_ENDPOINT",
    "http://minio:9000",
)

MINIO_ACCESS_KEY = os.getenv(
    "MINIO_ACCESS_KEY",
    "hiresense_admin",
)

MINIO_SECRET_KEY = os.getenv(
    "MINIO_SECRET_KEY",
    "hiresense_minio_password",
)

MINIO_BUCKET = os.getenv(
    "MINIO_BUCKET",
    "interview-videos",
)
RESUME_BUCKET = "hiresense-resumes"


s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=MINIO_ACCESS_KEY,
    aws_secret_access_key=MINIO_SECRET_KEY,
    region_name="us-east-1",
    config=Config(
        signature_version="s3v4",
    ),
)


def ensure_bucket() -> None:
    """
    Create the interview video bucket if it does not already exist.
    """

    try:
        s3_client.head_bucket(
            Bucket=MINIO_BUCKET
        )

    except Exception:
        s3_client.create_bucket(
            Bucket=MINIO_BUCKET
        )


def upload_interview_video(
    video_file,
    session_id: uuid.UUID,
    question_id: uuid.UUID,
) -> str:

    ensure_bucket()

    extension = ".webm"

    content_type = getattr(
        video_file,
        "content_type",
        None,
    )

    if content_type == "video/mp4":
        extension = ".mp4"

    object_name = (
        f"interviews/"
        f"{session_id}/"
        f"{question_id}/"
        f"{uuid.uuid4()}{extension}"
    )

    s3_client.upload_fileobj(
        video_file.file,
        MINIO_BUCKET,
        object_name,
        ExtraArgs={
            "ContentType": content_type
            or "video/webm",
        },
    )

    return object_name

def download_interview_video(
    object_name: str,
    output_path: str,
) -> str:
    """
    Download an interview video from MinIO to a local file.

    Args:
        object_name: MinIO object key stored in session_questions.video_url.
        output_path: Local filesystem path where the video should be saved.

    Returns:
        The local output path.
    """

    output_directory = os.path.dirname(output_path)

    if output_directory:
        os.makedirs(
            output_directory,
            exist_ok=True,
        )

    s3_client.download_file(
        MINIO_BUCKET,
        object_name,
        output_path,
    )

    return output_path


def ensure_resume_bucket() -> None:
    try:
        s3_client.head_bucket(Bucket=RESUME_BUCKET)
    except ClientError as exc:
        status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code not in {404, 301, 403}:
            raise
        s3_client.create_bucket(Bucket=RESUME_BUCKET)


def upload_resume(
    *,
    user_id: uuid.UUID,
    data: bytes,
    extension: str,
    content_type: str,
) -> str:
    ensure_resume_bucket()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    object_name = f"users/{user_id}/resume-{timestamp}{extension}"
    s3_client.upload_fileobj(
        BytesIO(data),
        RESUME_BUCKET,
        object_name,
        ExtraArgs={"ContentType": content_type},
    )
    return object_name


def delete_resume(object_name: str) -> None:
    ensure_resume_bucket()
    s3_client.delete_object(Bucket=RESUME_BUCKET, Key=object_name)


def download_resume(object_name: str, output_path: str) -> str:
    ensure_resume_bucket()
    output_directory = os.path.dirname(output_path)
    if output_directory:
        os.makedirs(output_directory, exist_ok=True)
    s3_client.download_file(RESUME_BUCKET, object_name, output_path)
    return output_path