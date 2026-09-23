import boto3

from app.config import settings


s3_client = boto3.client(
    "s3",
    region_name=settings.aws_region,
    endpoint_url=f"https://s3.{settings.aws_region}.amazonaws.com",
)


def upload_file(
    file_path: str,
    object_key: str,
    content_type: str | None = None,
) -> None:
    extra_args = {}

    if content_type:
        extra_args["ContentType"] = content_type

    s3_client.upload_file(
        file_path,
        settings.s3_bucket_name,
        object_key,
        ExtraArgs=extra_args,
    )


def download_file(object_key: str, file_path: str) -> None:
    s3_client.download_file(
        settings.s3_bucket_name,
        object_key,
        file_path,
    )

def generate_download_url(
    object_key: str,
    expiration: int = 300,
) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.s3_bucket_name,
            "Key": object_key,
        },
        ExpiresIn=expiration,
    )


def delete_file(object_key: str) -> None:
    s3_client.delete_object(
        Bucket=settings.s3_bucket_name,
        Key=object_key,
    )


def list_files() -> list[str]:
    response = s3_client.list_objects_v2(
        Bucket=settings.s3_bucket_name,
    )

    return [
        item["Key"]
        for item in response.get("Contents", [])
    ]