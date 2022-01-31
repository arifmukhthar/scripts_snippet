from cassandra.cluster import Cluster
import cassandraConfigs
import json
from urlparse2 import urlparse
import sqlite3


class CassandraDataService:
    cluster = None
    session = None

    def __init__(self, cluster_ip, keyspace):
        self.establish_connection_to_cluster(cluster_ip, keyspace)
        self.logger = Logger(cassandraConfigs.config['logfile'])

    def establish_connection_to_cluster(self, cluster_ip, keyspace):
        self.cluster = Cluster(cluster_ip)
        self.session = self.cluster.connect(keyspace)
        print self.session

    def get_table_data(self, table_name, field_names_to_query_array, key=None):
        field_names_to_query_string = ''.join(field_names_to_query_array)
        query = "SELECT {0} from {1}".format(field_names_to_query_string, table_name)
        if key is not None:
            query_input = " WHERE {0}"
            query += query_input.format(key)

        return self.session.execute(query)

    def update_table_data(self, table_name, fields_to_update_list, key, column1=None):

        print column1
        if table_name == "book_versions":
            update_query = """UPDATE {} SET value = '{}' WHERE key='{}' and column1={};""".format(table_name,fields_to_update_list[1], key, int(column1), )
        elif table_name == "books":
            update_query = """UPDATE {} SET thumbnailurl = '{}' WHERE key='{}';""".format(table_name, fields_to_update_list[1], key, )

        try:
            print "updating database: %s" % update_query
            self.session.execute(update_query)
            self.logger.log(key, table_name, 1, update_query)
        except Exception as e:
            print "database update failed"
            print repr(e)
            self.logger.log(key, table_name, 0, repr(e))

class EPSMigration:

    def __init__(self, cassandra_configuration):
        self.cassandra_data_service = CassandraDataService(cassandra_configuration.config['cluster_ip'],
                                                           cassandra_configuration.config['keyspace'])
        self.fields_needed_from_db = cassandraConfigs.config['fields_to_update']
        self.table_to_update = cassandraConfigs.config['table_to_update']

    def __parse_book_url__(self, book):

        if book[0] == None:
            print("skipping book: {0} because it has no value in one or all of fields".format(book.key))
            return

        try: #if field has json values
            book_url_json = json.loads(book.value)
            book_uri = urlparse(book_url_json['url'])
            book_path = book_uri.path.split("/api")
            book_domain = '{uri.scheme}://{uri.netloc}'.format(uri=book_uri) + book_path[0]
            return book_domain
        except: #if field has string values
            try:
                book_uri = urlparse(book.thumbnailurl)
            except:
                print("BAD BOOK KEY:{} COLUMN1:{}".format(book.key, book.column1))
                return None

            book_path = book_uri.path.split("/api")
            book_domain = '{uri.scheme}://{uri.netloc}'.format(uri=book_uri) + book_path[0]
            return book_domain

    def __replace_url_in_field__(self, book):

        try: #if field has json values

            #convert to json and parse the string
            book_url_json = json.loads(book.value)

            print("The field's value is JSON")
            book_url_string = book_url_json['url']

            #replace hostname to the new hostname and generate new fully qualified URL
            book_hostname = book_url_string.split("/api")
            book_url_string = book_url_string.replace(book_hostname[0], cassandraConfigs.urlToCheck[book_hostname[0]])

            #update json with new fully qualified URL
            book_url_json['url'] = book_url_string

            #return back the value as string to update in the table
            return [book._fields[0], (json.dumps(book_url_json))]

        except: #if field has string values

            book_url_string = book.thumbnailurl

            book_uri = urlparse(book.thumbnailurl)
            book_path = book_uri.path.split("/api")
            book_hostname = '{uri.scheme}://{uri.netloc}'.format(uri=book_uri) + book_path[0]

            print("The field value is String")
            book_url_string = book_url_string.replace(book_hostname, cassandraConfigs.urlToCheck[book_hostname])

            return [book._fields[0], book_url_string]




    def __update_book__(self, book, table_to_update):

        new_url_value = self.__replace_url_in_field__(book)
        self.cassandra_data_service.update_table_data(table_to_update, new_url_value, book.key, book.column1 if hasattr(book, 'column1') else None)
        return

    def __should_update_book_domain__(self, book_domain):

        if book_domain == None:
            return False

        for domains_to_be_replaced in cassandraConfigs.urlToCheck:
            if book_domain in domains_to_be_replaced:
                return True

        return False

    def execute(self):
        table_data = self.cassandra_data_service.get_table_data(self.table_to_update, self.fields_needed_from_db)

        try:
            for book in table_data:
                book_domain = self.__parse_book_url__(book)
                if self.__should_update_book_domain__(book_domain):
                    self.__update_book__(book, self.table_to_update)
                print (book.key)

        except Exception as e:
            print(e)


class Logger:
    def __init__(self, dbfile):
        self.conn = self.__initdb__(dbfile)

    def __initdb__(self, dbfile):
        conn = sqlite3.connect(dbfile)
        with conn:
            conn.execute("CREATE TABLE IF NOT EXISTS results (key text, tablename text, status text, message text);")

        return conn

    def log(self, key, table, status, message):
        print "logging key %s from table %s" % (key, table)
        with self.conn:
            self.conn.execute("insert into results(key, tablename, status, message) values(?,?,?,?)", (key,table,status,message))



def main():
    EPSMigration(cassandraConfigs).execute()


if __name__ == "__main__":
    main()
