import boto3
import csv
import time

client = boto3.client("logs")
""" :type: pyboto3.cloudwatchlogs """

log_group_names = []
log_dict = {}
log_dict_delete = {}
current_time = time.time() * 1000
six_months_ago_epoch = current_time - 15778476000


def get_log_groups():
    params = {}
    while True:

        try:
            response = client.describe_log_groups(**params)
        except Exception as e:
            print (e)

        if 'nextToken' not in response:
            for log in response['logGroups']:
                log_group_names.append(log['logGroupName'])
            break
        params['nextToken'] = response['nextToken']
        for log in response['logGroups']:
            log_group_names.append(log['logGroupName'])

    return log_group_names


def get_log_streams(log_group_names):
    for log_group in log_group_names:
        params = {}
        log_streams = []
        while True:
            params['logGroupName'] = log_group
            print(log_group)
            try:
                response = client.describe_log_streams(**params)
            except Exception as e:
                print (e)
            if 'nextToken' not in response:
                for log_stream in response['logStreams']:
                    log_streams.append(log_stream)
                log_dict[log_group] = [log_streams]
                print ("LogGroup:{0} - No more nextToken, moving on to get log streams from next LogGroup".format(log_group))
                break

            params['nextToken'] = response['nextToken']

            for log_stream in response['logStreams']:
                log_streams.append(log_stream)
            print ("LogGroup:{0} - has nextToken, getting more logStreams from the same LogGroup. nextToken ID:{1}".format(log_group, params['nextToken']))
            log_dict[log_group] = log_streams

    return log_dict


def check_if_delete_log_streams(log_dict):
    for log_group, log_streams_dict in log_dict.items():
        log_stream_delete_list = []
        for log_streams_list in log_streams_dict:
            for log_stream in log_streams_list:
                    if log_stream.get('lastEventTimestamp'):
                        if log_stream['lastEventTimestamp'] < six_months_ago_epoch or log_stream['storedBytes'] == 0:
                            log_stream_delete_list.append(log_stream['logStreamName'])
                            print("LogGroup:{0} LogStream:{1} - satisfies delete condition, adding logStream to delete list".format(log_group, log_stream['logStreamName']))
                    else:
                        log_stream_delete_list.append(log_stream['logStreamName'])
                        print("LogGroup:{0} LogStream:{1} - doesn't have a timestamp attribute, adding logStream to delete list anyway".format(log_group, log_stream['logStreamName']))
            log_dict_delete[log_group] = log_stream_delete_list


    return log_dict_delete

def set_retention_policy(log_group_names):

    for log_group in log_group_names:

       try:
           client.put_retention_policy(logGroupName=log_group,retentionInDays=180)
           print("Retention policy set to 180 days for LogGorup: {0}".format(log_group_names))
       except Exception as e:
           print ("couldn't set retenion policy for log group: {0}".format(log_group))

    return 0


def delete_log_streams(log_dict_delete):

    for log_group, log_stream_names_list in log_dict_delete.items():
        for log_stream_name in log_stream_names_list:
            try:
                client.delete_log_stream(logGroupName=log_group, logStreamName=log_stream_name)
                print("DELETED - LogStream: {0} from LogGroup:{1}".format(log_stream_name,log_group))
            except Exception as e:
                print("Could not delete LogStream: {0} from LogGroup:{1} EXCEPTION: {2}".format(log_stream_name, log_group, e))
    return 0

def delete_empty_log_groups(log_group_names):
    for log_group in log_group_names:
       try:
           log_group_attributes = client.describe_log_groups(logGroupNamePrefix=log_group)
           if log_group_attributes['logGroups'][0]['storedBytes'] == 0:
               client.delete_log_group(logGroupName=log_group)
               print("Deleted - LogGorup: {0} because it is empty".format(log_group))
       except Exception as e:
           print ("Exception while deleting log group: {0} , EXCEPTION: {1}".format(log_group, e))

    return 0


def main():
    get_log_groups()
    get_log_streams(log_group_names)
    check_if_delete_log_streams(log_dict)
    delete_log_streams(log_dict_delete)
    delete_empty_log_groups(log_group_names)
    set_retention_policy(log_group_names)

    print("cloudWatch Cleanup complete")





if __name__ == '__main__':
    main()
