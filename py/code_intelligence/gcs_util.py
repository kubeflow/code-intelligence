from google.cloud import storage
import logging

def check_file_in_gcs(bucket_name, gcs_filename):
    """
    Check if the file exists in the bucket in GCS.
    Args:
      bucket_name: bucket name, str
      gcs_filename: the file name that needs to be checked in GCS, str

    Return
    ------
    bool
        the file exists in the bucket or not
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    return storage.Blob(bucket=bucket, name=gcs_filename).exists(storage_client)

def upload_file_to_gcs(bucket_name, gcs_filename, local_filename):
    """
    Upload a local file to GCS.
    Args:
      bucket_name: bucket name, str
      gcs_filename: the file name that is stored in GCS, str
      local_filename: the local file that needs to be uploaded, str
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(gcs_filename)
    blob.upload_from_filename(local_filename)

def download_file_from_gcs(bucket_name, gcs_filename, local_filename):
    """
    Download a file in GCS to the local.
    Args:
      bucket_name: bucket name, str
      gcs_filename: the file name that is stored in GCS, str
      local_filename: the new local file, str
    """
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.get_blob(gcs_filename)
    with open(local_filename, 'wb') as f:
        blob.download_to_file(f)
