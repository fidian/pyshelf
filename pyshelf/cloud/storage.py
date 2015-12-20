from boto.s3.connection import S3Connection
from boto.s3.key import Key
import os
import math
from filechunkio import FileChunkIO
from pyshelf.cloud.stream_iterator import StreamIterator
from pyshelf.cloud.cloud_exceptions import ArtifactNotFoundError, BucketNotFoundError, DuplicateArtifactError, InvalidNameError


class Storage(object):
    def __init__(self, access_key, secret_key, bucket_name, logger):
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.logger = logger

    def connect(self):
        self.logger.debug("Attempting to establish connection")
        self.conn = S3Connection(self.access_key, self.secret_key)

    def close(self):
        self.logger.debug("Closing connection")
        self.conn.close()

    def get_artifact(self, artifact_name):
        """
            Returns an object that can be used as a generator.
            This should be used when streaming large files
            directly to the client.

            http://technology.jana.com/2015/03/12/using-flask-and-boto-to-create-a-proxy-to-s3/

            Args:
                bucketName(basestring): The name of the cloud storage bucket
                    (S3 right now) that we want to connect to
                artifactName(basestring): Full path to an object that you wish
                    to download.

            Returns:
                pyshelf.cloud.stream_iterator.StreamIterator: A object that
                    implements a generator interface so can be passed
                    directly into a response so long as the framework supports it.
        """
        key = self._get_key(artifact_name)
        self.logger.debug("Creating instance of pyshelf.cloud.stream_iterator.StreamIterator. Artifact {}".format(artifact_name))
        stream = StreamIterator(key)
        return stream

    def upload_artifact(self, artifact_path, artifact_name, src):
        """
            Uploads an artifact chunking any artifacts that exceed
            100 MB using FileChunkIO.

            Args:
                artifact_path(basestring): Path to upload artifact to
                artifact_name(basestring): Desired name for new artifact
                src(basestring): Path to file that will be uploaded

        """
        if artifact_name[0] == "_":
            raise InvalidNameError(artifact_name)
        bucket = self._get_bucket(self.bucket_name)
        
        if bucket.get_key(artifact_name) is not None:
            raise DuplicateArtifactError(artifact_name)
        src_size = os.stat(src).st_size
        """ arbitrarily chunked at 100 MB """
        chunk_size = 104857600
        chunk_count = int(math.ceil(src_size/float(chunk_size)))
        self.logger.debug("Initiating upload")
        mp = bucket.initiate_multipart_upload(artifact_name)
        
        for i in range(chunk_count):
            offset = chunk_size * i
            bytes = min(chunk_size, src_size - offset)
            with FileChunkIO(src, 'r', offset=offset, bytes=bytes) as fp:
                mp.upload_part_from_file(fp, part_num=i + 1)
        mp.complete_upload()
        self.logger.debug("Completed upload of {}".format(artifact_name))

    def delete_artifact(self, artifact_name):
        key = self._get_key(artifact_name)
        if key is None:
            raise ArtifactNotFoundError(artifact_name)
        key.delete()

    def _get_key(self, artifact_name):
        bucket = self._get_bucket(self.bucket_name)
        self.logger.debug("Attempting to get artifact {}".format(artifact_name))
        key = bucket.get_key(artifact_name)
        if key is None:
            self.logger.error("Artifact {}  does not exist in bucket {}".format(artifact_name, self.bucket_name))
            raise ArtifactNotFoundError(artifact_name)
        return key

    def _get_bucket(self, bucket_name):
        self.logger.debug("Attempting to get bucket {}".format(bucket_name))
        bucket = self.conn.lookup(self.bucket_name)
        if bucket is None:
            self.logger.error("Bucket {} does not exist".format(bucket_name))
            raise BucketNotFoundError(bucket_name)
        return bucket

    def __enter__(self):
        """ For use in "with" syntax"""
        self.connect()
        return self

    def __exit__(self, exception_type, exception, traceback):
        """ For use in "with" syntax"""
        # TODO : Properly handle exceptions.  For now they will
        # fly
        self.close()
        return False
