STEP 1: Run 'pip intall -r requirements.txt' to install dependencies.

STEP 2: In cassandraConfigs.py edit the config dictionary with one of cassandra IPs in the cluster (Run nodetool status in the cassandra node and pick any one IP), keyspace, fields for which URLs have to be updated (along with their primary key(s)), table in which the fields are present.

STEP 3: In cassandraConfigs.py edit the urlToCheck dictionary with <URL TO FIND>:<URL TO REPLACE>

STEP 4: Run replaceURL.py without any arguements 'python replaceURL.py > out.log'

NOTE: Check out.log file for keyword 'BAD BOOK' to find the IDs of books that did not have URLs replaced. These are likely books with tampered value in the URL field.

NOTE: The scipt only updates URLs for a single table at a time. Update table name and fileds to update values in the cassandraConfig.py file to replace URL for another table.