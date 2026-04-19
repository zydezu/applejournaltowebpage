import os

from dotenv import load_dotenv

load_dotenv()

R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
R2_ACCESS_KEY = os.environ.get("R2_ACCESS_KEY", "")
R2_SECRET_KEY = os.environ.get("R2_SECRET_KEY", "")
R2_BUCKET = os.environ.get("R2_BUCKET", "")
R2_PUBLIC_URL = os.environ.get("R2_PUBLIC_URL", "")

USE_R2 = bool(
    R2_ACCOUNT_ID and R2_ACCESS_KEY and R2_SECRET_KEY and R2_BUCKET and R2_PUBLIC_URL
)

s3_client = None
if USE_R2:
    import boto3

    s3_client = boto3.client(
        "s3",
        endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=R2_ACCESS_KEY,
        aws_secret_access_key=R2_SECRET_KEY,
        region_name="auto",
    )


def upload_to_r2(local_path, r2_key):
    if not s3_client:
        return False
    try:
        s3_client.upload_file(local_path, R2_BUCKET, r2_key)
        return True
    except Exception as e:
        print(f"R2 upload failed: {e}")
        return False
