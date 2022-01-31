This script frees up S3 space by deleting/aborting incomplete/in-progress multipart uploads across all S3 buckets in the AWS account.

The script can be executed with the below options:
--------------------------------------------------
`s3-cleanup.py --action [listMultipartUploads | cleanUpS3]`

listMultipartUploads - LISTS buckets that have multipart uploads incomplete/in-progress and gives an ESTIMATE of the SPACE SAVINGS if cleanup is done

cleanUpS3 - DELETES/aborts incomplete/in-progress multipart uploads across all S3 buckets. 



##notes
1. If the script is being run on an EC2 instance:
For authentication the script looks for aws access key and secret keys in ~/.aws/credentials.
If the credentials file doesn't exist, boto curls the metadata of the instance and uses a temp token generated using the IAM role attached to the instance.

2. If the script is run locally
  -add aws access key and secret key in ~/.aws/credentials using aws cli command `aws configure`.
 
