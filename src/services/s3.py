import boto3
import json
from datetime import datetime
from src.configs.configs import BUCKET_NAME

class MockS3():
    def check_exist_file(self, filepath):
        return False

class S3:
    def __init__(self, bucket_name=BUCKET_NAME):
        '''
        Class for handling AWS S3 Buckets methods
        '''
        self.bucket_name = bucket_name
        self.client = boto3.client('s3')
        self.resource = boto3.resource('s3')
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except:
            print('bucket not found')
            self.client.create_bucket
        

    def upload(self, data, filepath):
        '''
        Sends file to Bucket
        :params data: Data to be stored
        :params filepath: path inside bucket to store data
        '''
        self.client.put_object(Bucket=self.bucket_name, Body=data, Key=filepath)
        print('File sent to Bucket')

    def load(self, filepath):
        '''
        Load file into memory
        :params filepath: path inside bucket to file
        '''
        file = self.client.get_object(Bucket=self.bucket_name, Key=filepath)
        data = file['Body'].read()
        try:
            return json.loads(data)
        except:
            return data

    def signed_s3_file(self, filepath, expiration_time=86400):
        '''
        Makes a Signed URL to access a restricted file, valid for a given amount of time
        :params filepath: path inside bucket to file
        :params expiration_time: Time in seconds of how long this link can be used. 86400s = 24h
        '''
        response = self.client.generate_presigned_url('get_object',Params={'Bucket': self.bucket_name,'Key': filepath}, ExpiresIn=expiration_time)
        return response
    
    def latest_file(self, filepath='', date_limit=None):
        '''
        Runs through files and return the latest file modified
        :params filepath: path inside bucket of files. Used as prefix to increase search speed
        :params date_limit: minimum datetime value to be considered
        '''
        truncate = True
        payload = {
            'Bucket': self.bucket_name,
            'Prefix': filepath
        }
        latest_obj = None
        get_last_modified = lambda obj: int(obj['LastModified'].strftime('%s')) 
        while truncate:
            response = self.client.list_objects_v2(**payload)
            if response['IsTruncated']:
                payload['ContinuationToken'] = response['NextContinuationToken']
            else:
                truncate=False             
            if 'Contents' not in response:
                return None
            objs = response['Contents']
            latest_objs = [obj for obj in sorted(objs, key=get_last_modified, reverse=True)]
            if len(latest_objs) > 0:
                if latest_obj is None:
                    latest_obj = latest_objs[0]
                elif latest_objs[0]['LastModified'] > latest_obj['LastModified']:
                    latest_obj = latest_objs[0]

        if latest_obj is None:
            return None

        if date_limit is None:
            return latest_obj['Key']

        if latest_obj['LastModified'].replace(tzinfo=None) >= date_limit:    
            return latest_obj['Key']

        get_last_modified = lambda obj: int(obj['LastModified'].strftime('%s'))
        objs = self.client.list_objects_v2(Bucket=self.bucket_name, Prefix=filepath)
        if 'Contents' not in objs:
            return None
        objs = objs['Contents']
        latest_obj = [obj for obj in sorted(objs, key=get_last_modified, reverse=True) if obj['Key'].startswith(filepath)]
        if len(latest_obj) > 0:
            latest_obj = latest_obj[0]
        else:
            return None

    def check_exist_file(self, filepath):
        '''
        Checks if a file already exists on bucket
        :params filepath: path inside bucket to store data
        '''
        from botocore.errorfactory import ClientError
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=filepath)
            # print(f"The file {filepath} already exist!")
            return True
        except ClientError as e:
            if e.response["ResponseMetadata"]["HTTPStatusCode"] >= 400:
                return False

    def batch_files(self, path='', lower_limit=None, upper_limit=None):
        truncate = True
        files = []
        payload = {
            'Bucket': self.bucket_name,
            'Prefix': path
        }
        while truncate:
            response = self.client.list_objects_v2(**payload)
            if response['IsTruncated']:
                payload['ContinuationToken'] = response['NextContinuationToken']
            else:
                truncate=False             
            if 'Contents' not in response:
                return None
            objs = response['Contents']
            files.extend(objs)

        if lower_limit is None and upper_limit is None:
            yield from files        
        else:
            if lower_limit is not None:
                time_filter = lambda x: lower_limit <= x['LastModified'].replace(tzinfo=None)
                files = list(filter(time_filter, files))
            
            if upper_limit is not None:
                time_filter = lambda x: upper_limit >= x['LastModified'].replace(tzinfo=None)
                files = list(filter(time_filter, files))
            yield from files

    @staticmethod
    def data_lake_name():
        '''
        Standard filepath name for storing files and making a structured datalake
        '''
        today = datetime.today()
        today_folder = today.strftime('%Y/%m/%d')
        return today_folder