import boto3
import logging
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

connection = boto3.client('s3')

parser = argparse.ArgumentParser(description='Commandline argument parser.')
parser.add_argument('--action', help='Choose what report is required [listMultipartUploads|cleanUpS3].',
                    required=True)
action = parser.parse_args().action


def get_all_buckets():
    bucket_list = list()
    buckets = connection.list_buckets()
    for bucket_details in buckets['Buckets']:
        bucket_list.append(bucket_details['Name'])
    return bucket_list


# calculate each part's size
def get_parts_size(bucket, key, upload_id):
    try:
        part_details = connection.list_parts(Bucket=bucket, Key=key, UploadId=upload_id)
    except:
        print("MPU with transient Upload State in this bucket - Ignoring MPUs in this bucket")
        return 0
    if 'Parts' in part_details:
        return part_details['Parts'][0]['Size']
    else:  # some parts do not have size attribute
        return 0


def abort_multipart_uploads(bucket):
    bucket_details = connection.list_multipart_uploads(Bucket=bucket)
    parts_total_size = 0
    if 'Uploads' in bucket_details:
        for parts in bucket_details['Uploads']:
            upload_id = parts['UploadId']
            key = parts['Key']
            parts_total_size = parts_total_size + get_parts_size(bucket, key, upload_id)
            connection.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
            logger.info("Deleted multipart upload part [{0}] in Bucket: {1}".format(key, bucket))
        logger.info("Space recovered after cleaning up Bucket: {0} {1} Bytes".format(bucket, parts_total_size))

    else:
        logger.info("No incomplete/in-progress multipart uploads in bucket:{0}".format(bucket))

    return parts_total_size


def list_multipart_uploads(bucket):
    bucket_details = connection.list_multipart_uploads(Bucket=bucket)
    parts_total_size = 0
    if 'Uploads' in bucket_details:
        print("{0} : ".format(bucket))
        for parts in bucket_details['Uploads']:
            upload_id = parts['UploadId']
            key = parts['Key']
            parts_total_size = parts_total_size + get_parts_size(bucket, key, upload_id)
            print("{0}".format(key))
        print("-----------------")

    else:
        print("{0} : NO MULTIPART UPLOADS".format(bucket))
        print("-----------------")

    return parts_total_size


def main():
    buckets = get_all_buckets()
    parts_total_size = []
    if action == 'cleanUpS3':
        for bucket in buckets:
            cleaned_up_space = abort_multipart_uploads(bucket)
            parts_total_size.append(cleaned_up_space)
        print("Total space recovered after cleanup {0} GB".format(sum(parts_total_size) / (1024 ** 3)))
    elif action == 'listMultipartUploads':
        for bucket in buckets:
            if bucket == "test":
                print("Skipping test bucket")
                continue
            can_free_up = list_multipart_uploads(bucket)
            parts_total_size.append(can_free_up)
        print("{0} GB can be recovered/freed-up if we cleanup incomplete/in-progress multipart uploads from the buckets".format(sum(parts_total_size) / (1024 ** 3)))
    else:
        print("Invalid operation. Please use listMultipartUploads or cleanUpS3")
        exit(1)


if __name__ == '__main__':
    main()
