import os
import csv
import time
import argparse
import subprocess
import logging
import re
from difflib import SequenceMatcher


class NodeTree:

    def __init__(self):
        self.children = {}
        self.is_tail = False
        self.path = None

    def add_or_get(self, name):
        if name in self.children:
            return self.children[name]
        else:
            self.children[name] = NodeTree()
            return self.children[name]

    def check_for_sync(self, path=''):
        for name, node in self.children.items():
            child_path = path + '/' + name

            if os.path.exists(child_path):
                child_exists = True
            else:
                # child_exists = False
                child_exists = True

            if not child_exists:
                self.is_tail = True
                self.path = path or '/'
                self.children = {}
                break

        for name, node in self.children.items():
            child_path = path + '/' + name
            node.check_for_sync(child_path)

    def get_all_tails(self, out_arr):
        if self.is_tail:
            out_arr.append(self.path)
        else:
            for name, node in self.children.items():
                node.get_all_tails(out_arr)


class SyncService:

    def __calculate_msrsync_timing__(self, start_time, end_time):
        logging.debug("Calculating time taken for migration")
        local_start_time = time.asctime(time.localtime(start_time))
        local_end_time = time.asctime(time.localtime(end_time))
        time_taken_minutes = round((end_time - start_time) / 60, 3)
        return {'start_time': local_start_time, 'end_time': local_end_time, 'time_taken': time_taken_minutes}

    def __prepare_failed_log_file_for_remigration__(self, failed_log_file_abs_path):

        logging.debug("Preparing FAILED_LOGS.csv for re-migration")
        with open(failed_log_file_abs_path, mode="r") as failed_log, open("temp.csv", "w") as outFile:
            reader = csv.reader(failed_log, delimiter=',')
            writer = csv.writer(outFile, delimiter=',')
            header = next(reader)
            writer.writerow(header)
            logging.debug("Updating FAILED_LOGS.csv with READY_TO_MIGRATE status")
            for row in reader:
                writer.writerow([row[0], "READY_TO_MIGRATE"])
            os.rename("temp.csv", "FAILED_LOGS.csv")

    def __check_if_folder_needs_remigration__(self, failed_log_file_abs_path):
        logging.debug("Checking which folders needs re-migration")
        root = NodeTree()
        with open(failed_log_file_abs_path, mode="r") as failed_log:
            reader = csv.reader(failed_log, delimiter=',')
            next(reader)
            logging.debug("Iterating through each row in FAILED_LOGS.csv to find which folders to re-migrate")
            for row in reader:
                logging.debug("Failed File row: {}".format(row))
                file_path = row[0].split("/")
                node = root
                for dir_name in file_path[1:-1]:
                    node = node.add_or_get(dir_name)
                    if node.is_tail:
                        break
                else:
                    node.is_tail = True
                    node.path = row[0][:row[0].rindex('/')]
                    node.children = {}
        root.check_for_sync()
        paths_to_sync = []
        root.get_all_tails(paths_to_sync)
        return paths_to_sync

    def __validate_remigrated_files__(self, failed_log_file_abs_path, source_mount_point, destination_mount_point):
        with open(failed_log_file_abs_path, mode="r") as failed_log, open("temp.csv", "w") as outFile:
            reader = csv.reader(failed_log, delimiter=',')
            writer = csv.writer(outFile, delimiter=',')
            header = next(reader)
            writer.writerow(header)
            logging.debug("Checking if files remigrated successfully and updating the FAILED_LOGS.csv")
            for row in reader:
                file_name_destination = row[0].replace(source_mount_point, destination_mount_point)
                if os.path.exists(file_name_destination):
                    row[1] = "SUCCESS"
                    line = [row[0],row[1]]
                    writer.writerow(line)
                else:
                    row[1] = "FAILED"
                    line = [row[0], row[1]]
                    writer.writerow(line)
            os.rename("temp.csv", "FAILED_LOGS.CSV")
            logging.info("Updated FAILED_LOGS.csv with new migration status for failed files")

    def sync_files_between(self, source, destination, rsync_flags):
        start_time = time.time()
        logging.info("Starting msrsync between '{}' '{}'".format(source, destination))
        cmd = "msrsync -P -p 14 --stats --buckets logs --keep src dest --rsync '-{0}' {1} {2} >> msrsync_out.txt 2>> msrsync_err.txt".format(
            rsync_flags, source, destination)
        pwd = ""
        msrsync = subprocess.Popen('echo {} | sudo -S {}'.format(pwd, cmd), shell=True)
        logging.info(
            "Waiting for mrsync to complete sync between '{}' '{}' - Monitor mrsync_out and msrsync_err for more info".format(
                source, destination))
        msrsync.wait()  # Wait till msrsync completes migraiton
        logging.info(
            "Mrsync migration complete between '{}' '{}' - Check mrsync_out and msrsync_err for more info".format(
                source, destination))
        end_time = time.time()
        return self.__calculate_msrsync_timing__(start_time, end_time)

    def __find_source_destination_for_remigration__(self, folder, source_mount_point, destination_mount_point):
        if destination_mount_point in folder:
            seqMatch = SequenceMatcher(None, source_mount_point, folder)
            match = seqMatch.find_longest_match(0, len(source_mount_point), 0, len(folder))
            source = folder.replace(folder[0:match.b + match.size], source_mount_point[0:match.a + match.size])
            destination = folder
        elif source_mount_point in folder:
            source = folder
            destination = folder.replace(source_mount_point, destination_mount_point)

        return {"source": source,  "destination": destination} #adding trailing slash to source to avoid folder duplication in msrsync migration

    def remigrate_failed_files(self, failed_log_file_abs_path, source_mount_point, destination_mount_point,
                               rsync_flags):

        logging.info("Preparing for remigration from '{}' to '{}'".format(source_mount_point, destination_mount_point))

        if os.path.exists(failed_log_file_abs_path):
            self.__prepare_failed_log_file_for_remigration__(failed_log_file_abs_path)
            logging.debug("Identifying folders to remigrate based on missing files list in FAILED_LOG.csv")
            folders_to_migrate = self.__check_if_folder_needs_remigration__(failed_log_file_abs_path)
        logging.info("Remigrating between '{}' to '{}'".format(source_mount_point, destination_mount_point))
        for folder in folders_to_migrate:
            source_destination_dict = self.__find_source_destination_for_remigration__(folder, source_mount_point, destination_mount_point)
            logging.debug("Remigrating failed files between paths: {} and {}".format(source_destination_dict["source"], source_destination_dict["destination"]))
            self.sync_files_between(source_destination_dict["source"], source_destination_dict["destination"], rsync_flags)
        self.__validate_remigrated_files__(failed_log_file_abs_path, source_mount_point, destination_mount_point)


class LogService:
    errors_while_migration = ['file has vanished:', 'rsync: rename', 'rsync: link_stat']

    def __search_for_temp_log_directory__(self):
        logging.info("Searching for msrsync temp logs directory in current folder")

        log_directory = os.getcwd()

        logging.debug("Doing an os.walk in {} directory".format(log_directory))
        for path, subdirectories, files in os.walk(log_directory):
            logging.debug("Recursively checking path {} - Checking subdirectories {}".format(path, subdirectories))
            for subdir in subdirectories:
                logging.debug("Checking Subdirectory {} for msrsync folder".format(subdir))
                temp_log_folder_name = re.match("(msrsync\W+)", subdir)
                if temp_log_folder_name is not None:
                    logging.info(
                        "Msrsync temp log directory found: {}".format(os.path.join(path, temp_log_folder_name.string)))
                    return os.path.join(path, temp_log_folder_name.string)
        logging.warning("Msrsync temp log directory not found")
        return None

    def __search_log_files__(self, temp_log_directory, extension):
        log_files_abs_path = []

        for dirpath, dirnames, files in os.walk(temp_log_directory):
            for name in files:
                if extension and name.lower().endswith(extension):
                    log_files_abs_path.append(os.path.join(dirpath, name))
                elif not extension:
                    log_files_abs_path.append(dirpath, name)
                else:
                    logging.warning("No  *.log files found in temp log directory {}".format(temp_log_directory))
        return log_files_abs_path

    def __parse_temp_logs__(self, log_files_abs_path):
        failed_files_dict = {}

        for log_file in log_files_abs_path:
            logging.debug("Parsing log files {}".format(log_file))
            with open(log_file, mode='r') as log:
                for line in log:
                    for error in self.errors_while_migration:
                        if error in line:
                            logging.debug("Failed file found: {}".format(line))
                            match = re.match(
                                "([0-9\/]+) ([0-9:]+) (\[[0-9]+\]) ([a-z :_]+) \"([\/A-Za-z0-9-_.]+)\"(.*)", line)
                            print("Group" + match.group())
                            failed_file = match.group(5)
                            error_type = match.group(4)
                            failed_files_dict[failed_file] = error_type
            log.close()

        return failed_files_dict

    def __write_new_logs_to_csv__(self, failed_files_abs_path_from_logs):
        failed_log_file_name = "FAILED_LOGS.csv"
        logging.info("Generating CSV with failed files list: {}".format(failed_log_file_name))

        with open(failed_log_file_name, mode='w') as logs_csv:
            log_file = csv.DictWriter(logs_csv, fieldnames=["FILE_NAME", "MIGRATION_STATUS"])
            log_file.writeheader()

            for key, value in failed_files_abs_path_from_logs.iteritems():
                log_file.writerow({'FILE_NAME': key, 'MIGRATION_STATUS': value})

        return failed_log_file_name

    def delete_old_migration_logs(self):
        temp_log_directory = self.__search_for_temp_log_directory__()

        if temp_log_directory:
            cmd = "rm -rf {}".format(temp_log_directory)
            pwd = ""
            rm_logs = subprocess.Popen('echo {} | sudo -S {}'.format(pwd, cmd), shell=True)
            logging.info("Removing old log directory: {}".format(temp_log_directory))
            rm_logs.wait()  # Wait till rm_logs removes tmp log directory
        else:
            logging.info("Old migration logs not found")

    def create_log_folder(self):
        if os.path.exists(os.getcwd() + "/logs"):
            logging.info(
                "Logs path: {}/logs already exists - using this folder to dump msrsync temp logs".format(os.getcwd()))
            return None
        else:
            cmd = "mkdir logs"
            pwd = ""
            create_log_folder = subprocess.Popen('echo {} | sudo -S {}'.format(pwd, cmd), shell=True)
            create_log_folder.wait()
            if os.path.exists(os.getcwd() + "/logs"):
                logging.debug("Logs path: {}/logs created - Msrsync temp logs are dumped here".format(os.getcwd()))

    def __check_access_to_log_files__():
        pass

    def generate_failed_files_logs(self):

        logging.info('Generating Failed files list from msrsync temp logs')
        temp_log_directory = self.__search_for_temp_log_directory__()
        if temp_log_directory is not None:
            logging.info("Msrsync temp log directory: {}".format(temp_log_directory))
            logging.info("Searching for *.log files in temp log directory {}".format(temp_log_directory))
            log_files_abs_path = self.__search_log_files__(temp_log_directory, ".log")

            if log_files_abs_path is not None:
                logging.info("*.log files found in temp log directory {}".format(temp_log_directory))
                logging.info("Searching for files failed to migrate from *.log files {}".format(temp_log_directory))
                failed_files_abs_path_from_logs = self.__parse_temp_logs__(log_files_abs_path)

                if failed_files_abs_path_from_logs:
                    logging.info("Found failed files during migration")
                    failed_log_file_name = self.__write_new_logs_to_csv__(failed_files_abs_path_from_logs)
                    logging.info("Generated CSV with failed files list: {}".format(failed_log_file_name))

                else:
                    logging.warning("No files failed during migration")
                    return 0
            else:
                logging.error("No *.log files found in  temp directory: {}".format(temp_log_directory))
                return 0
        else:
            logging.error(
                "Msrsync temp directory not found in 'logs' folder. Please check the directory manually and re-run the script with sudo permissions")
            return 0

    def generate_timing_logs(self, start_time, end_time, time_taken, source, destination):
        logging.info("Generating timing logs for the migration")
        with open("timesheet.csv", mode="a") as timesheet:
            timesheet_file = csv.DictWriter(timesheet, fieldnames=["SOURCE", "DESTINATION", "START_TIME", "END_TIME",
                                                                   "TIME_TAKEN"])
            timesheet_file.writeheader()
            timesheet_file.writerow(
                {'SOURCE': source, 'DESTINATION': destination, 'START_TIME': start_time, 'END_TIME': end_time,
                 'TIME_TAKEN': time_taken})
        logging.info("Timing logs generated, please check timesheet.csv for more details")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['sync', 'remigrate', 'generate-logs'],
                        help="1. Use 'sync' mode with source, destination and rsync flags to run a normal rsync. \n "
                             "2. Use 'remigrate' mode with absolute path to 'FAILED_LOGS.csv' to run the script in re-migration mode \n"
                             "3. Use 'generate-logs' mode  run the script to only generate a list of failed files from previous migration. This mode fails if 'logs' directory has been cleared",
                        required=True)
    parser.add_argument('--source', help='Specify the source folder to be migrated', required=True)
    parser.add_argument('--destination', help='Specify the destination folder here to be migrated', required=True)
    parser.add_argument('--rsync_flags', help="Specify flags for msrsync's rsync workers", required=True)
    parser.add_argument('--logging_level', choices=['debug', 'info'],
                        help="Specify the logging level and monitor rfsync.log file, default is INFO", default="info",
                        required=False)
    args = parser.parse_args()

    # set logging level
    if args.logging_level == 'debug':
        logging.basicConfig(level=logging.DEBUG, filename='rfsync.log', filemode='a',
                            format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')
    else:
        logging.basicConfig(level=logging.INFO, filename='rfsync.log', filemode='a',
                            format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')

    # select mode
    if args.mode == 'sync':
        logging.info("Running script in sync mode. File sync between Source: {} - Destination: {}".format(args.source,
                                                                                                          args.destination))
        sync = SyncService()
        logs = LogService()

        logs.create_log_folder()
        logging.info("Removing old msrsync log files from previous migrations")
        #logs.delete_old_migration_logs()
        msrsync = SyncService.sync_files_between(sync, args.source, args.destination, args.rsync_flags)
        #logs.generate_failed_files_logs()
        logs.generate_timing_logs(source=args.source, destination=args.destination, start_time=msrsync['start_time'],
                                  end_time=msrsync['end_time'], time_taken=msrsync['time_taken'])
    elif args.mode == 'remigrate':
        sync = SyncService()
        logs = LogService()

        logging.info("Creating log directory: '{}' for dumping msrsync temp log files".format(os.getcwd() + "/logs"))
        logs.create_log_folder()
        logging.info("Removing old msrsync log files from previous migrations")
        #logs.delete_old_migration_logs()
        logging.info("Running script in remigrate mode. File sync between Source: {} - Destination: {} - rsync_flags: {}".format(args.source, args.destination, args.rsync_flags))

        sync.remigrate_failed_files(failed_log_file_abs_path="{}/FAILED_LOGS.csv".format(os.getcwd()),
                                    source_mount_point=args.source,
                                    destination_mount_point=args.destination, rsync_flags=args.rsync_flags)
        logging.info("Remigration complete - check FAILED_LOGS.csv for migration status")


    elif args.mode == 'generate-logs':
        logging.info("Running script in generate-logs mode. NOTE: This mode doesn't migrate any files")

        logs = LogService()
        logs.generate_failed_files_logs()


if __name__ == "__main__":
    main()
