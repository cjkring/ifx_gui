import logging
import boto3
from config import read_config, validate_config
from os import path
from datetime import datetime

from botocore.exceptions import ClientError

def awsExport(config, filename):

    # Upload the file
    aws_config = config['aws']
    s3 = getBotoResource(aws_config)
    table = aws_config['table']
    bucket = s3.Bucket(aws_config['bucket'])
    basename = path.basename(filename)
    aws_name = f'{table}/{basename.replace("_","/")}'
    from logging import getLogger

    try:
        prev = round( time(), 3 )
        bucket.upload_file(filename, aws_name)
        now = round( time(), 3 )
        logging.getLogger(__name__).info(f'awsUpload {basename} as {aws_name} in {now-prev} seconds')

    except Exception as e:
        logging.getLogger(__name__).exception('Caught exception in awsExport')
        return False    
    return True

def getBotoResource(aws_config):

    if 'endpoint_url' in aws_config:
        return boto3.resource( 's3',
                                endpoint_url = aws_config['endpoint_url'],
                                aws_access_key_id = aws_config['key_id'],
                                aws_secret_access_key = aws_config['key'],
                                region_name = aws_config['region'] )
    else:
        return boto3.resource( 's3',
                                aws_access_key_id = aws_config['key_id'],
                                aws_secret_access_key = aws_config['key'],
                                region_name = aws_config['region'] )

# TEST code 
if  __name__ == "__main__":

    config = read_config()
    if validate_config(config) == False:
        quit()
    data = config['app']['data']
    filename = path.join(data,'chuck_awstest.txt') #should end up in the bucket as chuck/awstest.txt
    with open(filename, 'w') as f:
        f.write(f'Chuck awstest: {datetime.today()}')

    awsExport(config, filename)
    #awsImport(config, filename)

    #aws_config = config['aws']

    #bucket_name = aws_config['bucket']
    #s3 = getBotoResource(aws_config)
    #if s3 == None:
    #    quit()

    #bucket = s3.Bucket(bucket_name)
    # endpoint_url 
    #print(bucket)
    
    #print(dir(bucket))
    #try:
    #    bucket.upload_file('test.txt','test9.txt')
    #except Exception as e:
    #    print(f"Exception uploading file: {e}")
    #try:
    #    bucket.download_file('test1.txt','test2.txt')
    #except Exception as e:
    #    print(f"Exception uploading file: {e}")