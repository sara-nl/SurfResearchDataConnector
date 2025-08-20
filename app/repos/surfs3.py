import logging
import os
from pathlib import Path
import boto
import boto.s3.connection

logger = logging.getLogger()


class Surfs3(object):
    
    def __init__(self, api_key, user, api_address=None, *args, **kwargs):
        try:
            self.api_address = api_address
            if api_address is None:
                self.api_address = os.getenv(
                    "SURFS3_API_ADDRESS", "objectstore.surf.nl"
                )

            self.api_key = api_key
            self.user = user

            self.s3connection = boto.connect_s3(
                aws_access_key_id=user,
                aws_secret_access_key=api_key,
                host = 'objectstore.surf.nl',
                calling_format = boto.s3.connection.OrdinaryCallingFormat(),
                )
        except Exception as e:
            logger.error(f"Exception at init: {e}")

    def check_token(self):
        """Check the API-Token `api_key`.

        Returns `True` if the token is correct and usable, otherwise `False`."""
        try:
            s3buckets = self.s3connection.get_all_buckets()
            return True
        except Exception as e:
            logger.error(f"Exception at check_token: {e}")
            return False


    def create_new_bucket(self, metadata):
        try:
            buckets =self.s3connection.get_all_buckets()
            existing_bucket_names = [bucket.name for bucket in buckets]
            if metadata['s3archivename'] not in existing_bucket_names:
                self.s3connection.create_bucket(metadata['s3archivename'])
                buckets =self.s3connection.get_all_buckets()
                existing_bucket_names = [bucket.name for bucket in buckets]
                if metadata['s3archivename'] in existing_bucket_names:
                    return True
                else:
                    logger.error('Failed to create new bucket')
                    return {'message': 'Failed to create new bucket'}
            else:
                logger.error('Bucket name already exists')
                return {'message' : 'Bucket name already exists'}
        except Exception as e:
            logger.error(f"Exception at create_new_bucket: {e}")
            return {'message': f'Failed to create new bucket: {e}'}


    def upload_new_file_to_bucket(self, bucket_name, path_to_file):
        try:
            bucket = self.s3connection.get_bucket(bucket_name)
            key_name = path_to_file.split("./ARCHIVE/files/")[-1]
            key_name = key_name.split("./ARCHIVE/")[-1]
            key = bucket.new_key(key_name)
            key.set_contents_from_filename(path_to_file)
            if key_name in [item.name for item in bucket.list()]:
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Exception at upload_new_file_to_bucket: {e}")
            return False


    def get_bucket_content(self, bucket_name):
        try:
            repo_content = []
            bucket_name = bucket_name.split("https://")[-1]
            bucket = self.s3connection.get_bucket(bucket_name=bucket_name)
            for obj in bucket.list():
                filename = obj.key
                obj.base64md5
                tmp = {}
                tmp['name'] = obj.key
                tmp['size'] = obj.size
                tmp['link'] = ""
                tmp['hash'] = obj.md5
                tmp['hash_type'] = 'md5'
                repo_content.append(tmp)
            return repo_content
        except Exception as e:
            logger.error(f"Exception at download_files: {e}")

    def download_files(self, bucket_name, dest_folder):
        try:
            bucket_name = bucket_name.split("https://")[-1]
            bucket = self.s3connection.get_bucket(bucket_name=bucket_name)
            for obj in bucket.list():
                filename = obj.key.split("./")[-1]
                localfilepathname = os.path.join(dest_folder, filename)
                onlyfilename = localfilepathname.split("/")[-1]
                localdirpath = Path(localfilepathname.split(onlyfilename)[0])
                if not localdirpath.exists():
                    r = localdirpath.mkdir(parents=True)
                if not os.path.exists(localfilepathname):
                    with open(localfilepathname, 'w'):
                        pass
                obj.get_contents_to_filename(localfilepathname)
            return True
        except Exception as e:
            logger.error(f"Exception at download_files: {e}")
            return False
