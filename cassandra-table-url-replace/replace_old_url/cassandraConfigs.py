

config = {
    'cluster_ip': ['127.0.0.1'],
    'keyspace': 'bay',
    'fields_to_update': 'value,key,column1',
    'table_to_update': 'book_versions',
    'logfile': 'migration.db'
}

urlToCheck = {
    'URLOLD': 'URLNEW'
}

# for book_versions table, update the config dict with these values
# 'fields_to_update': 'value,key,column1',
# 'table_to_update': 'book_versions',

# for books table, update the config dict with these values
# 'fields_to_update': 'thumbnailurl,key',
# 'table_to_update': 'books',
