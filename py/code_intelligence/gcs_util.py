from google.cloud import storage
import logging
import re

GCS_REGEX = re.compile("gs://([^/]*)(/.*)?")

def split_gcs_uri(gcs_uri):
  """Split a GCS URI into bucket and path."""
  m = GCS_REGEX.match(gcs_uri)
  bucket = m.group(1)
  path = ""
  if m.group(2):
    path = m.group(2).lstrip("/")
  return bucket, path

def check_gcs_object(gcs_path, storage_client=None):
    """Check if the file exists in the bucket in GCS.
  
    Args:      
      gcs_path: the file name that needs to be checked in GCS, str
      storage_client: client to bundle configuration needed for API requests

    Return
    ------
    bool
        the file exists in the bucket or not
    """
    bucket_name, gcs_file_name = split_gcs_uri(gcs_path)
    return check_file_in_gcs(bucket_name, gcs_file_name, storage_client=storage_client)

def check_file_in_gcs(bucket_name, gcs_filename, storage_client=None):
    """
    Check if the file exists in the bucket in GCS.
    Args:
      bucket_name: bucket name, str
      gcs_filename: the file name that needs to be checked in GCS, str
      storage_client: client to bundle configuration needed for API requests

    Return
    ------
    bool
        the file exists in the bucket or not
    """
    if not storage_client:
        storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    return storage.Blob(bucket=bucket, name=gcs_filename).exists(storage_client)

def copy_to_gcs(local_file, gcs_path, storage_client=None):
    """ Upload a local file to GCS.
    Args:
      local_filename: the local file that needs to be uploaded, str      
      gcs_filename: the file name that is stored in GCS, str      
      storage_client: client to bundle configuration needed for API requests
    """
    bucket_name, gcs_file_name = split_gcs_uri(gcs_path)
    return upload_file_to_gcs(bucket_name, gcs_file_name, local_file, storage_client=storage_client)
  
def upload_file_to_gcs(bucket_name, gcs_filename, local_filename, storage_client=None):
    """
    Upload a local file to GCS.
    Args:
      bucket_name: bucket name, str
      gcs_filename: the file name that is stored in GCS, str
      local_filename: the local file that needs to be uploaded, str
      storage_client: client to bundle configuration needed for API requests
    """
    if not storage_client:
        storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(gcs_filename)
    blob.upload_from_filename(local_filename)


def copy_from_gcs(gcs_path, local_filename, storage_client=None):
    """
    Download a file in GCS to the local.
    Args:
      gcs_path: gcs path
      local_filename: the new local file, str
      storage_client: client to bundle configuration needed for API requests
    """
    bucket_name, gcs_file_name = split_gcs_uri(gcs_path)
    return download_file_from_gcs(bucket_name, gcs_file_name, local_filename, storage_client=storage_client)    
    
def download_file_from_gcs(bucket_name, gcs_filename, local_filename, storage_client=None):
    """
    Download a file in GCS to the local.
    Args:
      bucket_name: bucket name, str
      gcs_filename: the file name that is stored in GCS, str
      local_filename: the new local file, str
      storage_client: client to bundle configuration needed for API requests
    """
    if not storage_client:
        storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.get_blob(gcs_filename)
    with open(local_filename, 'wb') as f:
        blob.download_to_file(f)
