import boto3
import configparser
import os
import ntpath
import time

from settings import INPUT_DIR, AWS_RESULT_OBJECT, CONFIG_FILE


class S3Manager:
    def __init__(self):
        params = configparser.ConfigParser()
        params.read(CONFIG_FILE)
        self.s3 = boto3.client('s3', aws_access_key_id=params.get("DEFAULT", "access_key_id"),
                               aws_secret_access_key=params.get("DEFAULT", "secret_access_key"))
        self.aws_s3_bucket = params.get("DEFAULT", "s3_bucket_name")
        self.aws_s3_object = params.get("DEFAULT", "pdf_folder_object")
        self.download_completion = False

    def download_files(self, processed_files=None):
        if processed_files is None:
            processed_files = []
        downloaded_files = processed_files
        while True:
            object_listing = self.s3.list_objects_v2(Bucket=self.aws_s3_bucket, Prefix=self.aws_s3_object)

            for obj in object_listing['Contents']:
                path, filename = os.path.split(obj["Key"])
                if AWS_RESULT_OBJECT in path:
                    continue
                if filename != "":
                    if filename not in downloaded_files:
                        file_path = os.path.join(INPUT_DIR, filename)
                        print(f"[INFO] {filename} downloading...")
                        self.s3.download_file(self.aws_s3_bucket, obj["Key"], file_path)
                        downloaded_files.append(filename)
            time.sleep(1800)

        # self.download_completion = True

    def upload_files(self, file_path):
        file_name = ntpath.basename(file_path)
        path_on_s3 = AWS_RESULT_OBJECT + "/" + file_name
        self.s3.upload_file(file_path, self.aws_s3_bucket, path_on_s3)
        print(f"[INFO] Successfully upload {file_name}.")

        return


if __name__ == '__main__':
    S3Manager().download_files()
