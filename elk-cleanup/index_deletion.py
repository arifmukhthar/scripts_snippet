import argparse
import boto3
from requests_aws4auth import AWS4Auth
from elasticsearch import Elasticsearch, RequestsHttpConnection
import curator

region = 'us-east-1'
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)


def main():
    host, prefix, action, timestring = validate_input()

    requested_action = {
        "deleteIndex": deleteIndex

    }

    requested_action[action](host,prefix,timestring)


def validate_input():

    validHost = ['test.us-east-1.es.amazonaws.com',
                 'test1.us-east-1.es.amazonaws.com',
                 'test2.us-east-1.es.amazonaws.com']
    validActions = ['deleteIndex']
    validPrefixes = ['dev_','nonprod','telemetry-','eb_', 'smoke_', 'nightly_', 'perf_', 'cert_', 'ppe_']
    validTimestrings = ['%Y.%m','%Y-w%W','%Y-%m']

    parser = argparse.ArgumentParser(description='Commandline argument parser for AWS boto.')
    parser.add_argument('--host', help='Name of the ELK domain endpoint, choose one from ELK My Domain', required=True)
    parser.add_argument('--action', help='Choose what action is required [deleteIndex].', required=True)
    parser.add_argument('--prefix', help='Choose what prefix is required [deleteIndex].', required=True)
    parser.add_argument('--timestring', help='Choose what timestring is required [deleteIndex].', required=True)


    host = parser.parse_args().host
    action = parser.parse_args().action
    prefix = parser.parse_args().prefix
    timestring = parser.parse_args().timestring

    if host not in validHost:
        raise Exception('Host: ' + host + ' not recognized. Valid hosts are: ' + ' or '.join(validHost))
    if action not in validActions:
        raise Exception('Action: ' + action + ' not recognized. Valid actions are: ' + ' or '.join(validActions))
    if prefix not in validPrefixes:
        raise Exception('Prefix: ' + prefix + ' not recognized. Valid prefixes are: ' + ' or '.join(validPrefixes))
    if timestring not in validTimestrings:
        raise Exception('Prefix: ' + timestring + ' not recognized. Valid timestrings are: ' + ' or '.join(validTimestrings))



    return host, prefix, action, timestring

# delete index starts here.
def deleteIndex(host,prefix, timestring):

    # Build the Elasticsearch client.
    es = Elasticsearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )


    index_list = curator.IndexList(es)

     # Filters by naming prefix.
    index_list.filter_by_regex(kind='prefix', value=prefix)

    # Filters by age, anything with a time stamp older than 60 days or 2 months in the index name.
    if timestring == '%Y.%m' or timestring == '%Y-%m':
        index_list.filter_by_age(source='name', direction='older', timestring=timestring, unit='months', unit_count=2)
    if timestring == '%Y-w%W':
        index_list.filter_by_age(source='name', direction='older', timestring=timestring, unit='weeks', unit_count=8)




    # Filters by age, anything created more than 60 days.
    #index_list.filter_by_age(source='creation_date', direction='older', unit='days', unit_count=60)

    print("Found %s indices to delete" % len(index_list.indices))

    # If our filtered list contains any indices, delete them.
    if index_list.indices:
        curator.DeleteIndices(index_list).do_action()

if __name__ == '__main__':
    main()
