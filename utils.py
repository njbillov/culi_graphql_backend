import uuid
import hashlib
from typing import Tuple

import boto3
import tempfile
import shutil
import os
from config import BUCKET
from botocore.exceptions import ClientError


def hash_password(algorithm, password, salt):
    """Return database formatted password."""
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + password
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()
    password_db_string = "$".join([algorithm, salt, password_hash])
    return password_db_string


def create_password(password, algorithm='sha512'):
    """Create salt and format password."""
    salt = uuid.uuid4().hex
    return hash_password(algorithm, password, salt)


def create_key(file, algorithm='sha512'):
    hash_obj = hashlib.new(algorithm)
    hash_hex = hash_obj.hexdigest(file)
    return hash_hex


def compare_password(db_password, password):
    """Compare password from form and db."""
    # obtain the correct salt from database
    salt = (db_password).split('$')[1]
    password_db = (db_password).split('$')[2]

    # hash the password from the form using the correct salt
    algorithm = 'sha512'
    hash_obj = hashlib.new(algorithm)
    password_salted = salt + password
    hash_obj.update(password_salted.encode('utf-8'))
    password_hash = hash_obj.hexdigest()

    return password_db == password_hash


def upload_file(key: str, filename: str, bucket=BUCKET) -> Tuple[bool, str]:
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(filename, bucket, key)
    except ClientError as e:
        print(e)
        return False, key
    return True, key


def upload_object(key: str, content: str, tags="", bucket: str = BUCKET) -> Tuple[bool, str]:
    # tag_param = ''
    # if tags is not None:
    #     tag_param = "&".join([f'key{i + 1}={tag}' for i, tag in enumerate(tags)])
    s3_client = boto3.client('s3')
    try:
        response = s3_client.put_object(Key=key, Bucket=bucket, Body=content, Tagging=tags)
    except ClientError as e:
        print(e)
        return False, key
    return True, key


def test_get_object():
    s3_client = boto3.client('s3')
    obj = s3_client.get_object(Bucket=BUCKET, Key="test_object")
    print(obj['Body'].read().decode('utf-8'))


def sha256sum(filename):
    """Return sha256 hash of file content, similar to UNIX sha256sum."""
    content = open(filename, 'rb').read()
    sha256_obj = hashlib.sha256(content)
    return sha256_obj.hexdigest()


def save_file(file_input) -> (str, str):
    """Encrypt file name and save."""
    # Save POST request's file object to a temp file
    dummy, temp_filename = tempfile.mkstemp()
    file_input.save(temp_filename)

    # Compute filename
    hash_txt = sha256sum(temp_filename)
    print(hash_txt)
    dummy, suffix = os.path.splitext(file_input.filename)
    print(suffix)
    hash_filename_basename = hash_txt + suffix
    hash_filename = os.path.join(
        'tmp/',
        hash_filename_basename
    )

    # Move temp file to permanent location
    shutil.move(temp_filename, hash_filename)

    return hash_filename_basename, hash_filename


def presign_object(key: str, request_type='get_object'):
    s3_client = boto3.client('s3')
    print("trying to request a presigned url for test_object")
    try:
        response = s3_client.generate_presigned_url(request_type,
                                                    Params={'Bucket': BUCKET,
                                                            'Key': key},
                                                    ExpiresIn=600)
    except ClientError as e:
        print("Error getting presigned URL")
        return None

    print(response)

    return response
