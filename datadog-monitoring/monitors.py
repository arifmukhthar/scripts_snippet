from datadog import initialize, api
import yaml
import logging
import argparse

class DDMonitorsService:

    def __init__(self, api_key, application_key):
        self.establish_connection_to_datadog(api_key, application_key)
        self.load_monitor_configs("application_monitors_configs.yaml")

    def establish_connection_to_datadog(self, api_key, application_key):
        options = {
            'api_key': api_key,
            'app_key': application_key
        }
        initialize(**options)

    def load_monitor_configs(self, monitors_config_yaml):
        self.application_monitors_configs = yaml.load(open(monitors_config_yaml, 'r'))
        return self.application_monitors_configs

    def generate_custom_tag_and_name_for_monitors(self, for_metric, service_threshold_configs):

        service_name = service_threshold_configs['apm_name']

        service_tag = 'service:' + service_name
        custom_metric_tag = 'monitored_metric:' + for_metric
        environment_tag = 'env:prod'

        monitor_name = "Service {} has a high {} on env:prod".format(service_name, for_metric)
        tags = [environment_tag, service_tag, custom_metric_tag]

        return tags, monitor_name

    def generate_custom_monitoring_formula(self, for_metric, service):

        service_name = service['apm_name']
        response_time = service['response-time']
        throughput = service['throughput']
        error_rate = service['error-rate']

        if for_metric == "response-time":
            query = "avg(last_5m):avg:trace.servlet.request.duration.by.service.95p{env:prod,service:" + service_name + "} >= " + response_time
        elif for_metric == "throughput":
            query = "avg(last_1m):sum:trace.servlet.request.hits{env:prod,service:" + service_name + "}.as_rate() > " + throughput
        elif for_metric == "error-rate":
            query = "avg(last_1m):sum:trace.servlet.request.errors {env:prod,service:" + service_name + \
                    "} / sum:trace.servlet.request.hits{env:prod,service:" + service_name + "} >= " + \
                    error_rate
        return query

    def generate_custom_configs_for_datadog(self, for_metric, service_threshold_configs):

        logging.info("Generating Custom Configs for Creating/Editing Monitors")

        generated_tags, generated_monitor_name = self.generate_custom_tag_and_name_for_monitors(for_metric,
                                                                                                service_threshold_configs)
        generated_formula = self.generate_custom_monitoring_formula(for_metric, service_threshold_configs)

        logging.info("Generated Tags: {} \n Generated Name: {} \n Generated Formula: {}".format(generated_tags,
                                                                                                generated_monitor_name,
                                                                                                generated_formula))
        return generated_tags, generated_monitor_name, generated_formula

    def create_monitor(self, generated_tags, generated_monitor_name, generated_formula):

        monitor_options = {
            "notify_no_data": True,
            "no_data_timeframe": 10,
            "renotify_interval": 3
        }

        response = api.Monitor.create(
            type="query alert",
            query=generated_formula,
            name=generated_monitor_name,
            message="@test@test.com",
            tags=generated_tags,
            options=monitor_options)

        try:
            if response['id']:
                logging.info("Created metrics for {} with Monitor ID:".format(generated_tags, response['id']))

        except:
            logging.info("Unable to create metrics for {}. Exception: {}".format(generated_tags, response['errors'][0]))

    def edit_monitor(self, existing_monitor_id, generated_formula):

        response = api.Monitor.update(
            existing_monitor_id,
            query=generated_formula,
            message="@test@test.com"
        )

        if response['query'] == generated_formula:
            logging.info("Updated Monitor ID: {} with new values".format(existing_monitor_id))
        else:
            logging.info("Error, unable to edit monitor id:".format(existing_monitor_id))

    def view_monitor(self, monitor_id):
        existing_monitor = api.Monitor.get(monitor_id)
        return existing_monitor

    def check_if_create_or_edit_monitor(self, for_metric, service, generated_formula):

        monitor_search = api.Monitor.search(
            query='env:prod service:{} tag:"monitored_metric:{}"'.format(service['apm_name'], for_metric))

        try:
            fetched_metric = str(monitor_search['counts']['tag'][1]['name']).split(":")[1]
            fetched_monitor_name = str(monitor_search['counts']['tag'][2]['name']).split(":")[1]

            if for_metric in fetched_metric and service['apm_name'] in fetched_monitor_name:
                monitor_id = monitor_search['monitors'][0]['id']
                existing_monitor_configs = self.view_monitor(monitor_id)
                existing_formula = existing_monitor_configs['query']
                if existing_formula != generated_formula:
                    return "edit", monitor_id
        except:
            return "create", None

        return "skip", None

    def create_or_edit_monitor(self, for_metric, service_threshold_configs):
        logging.info("\n \n \n------------------------------------------------------------")
        generated_tags, generated_monitor_name, generated_formula = self.generate_custom_configs_for_datadog(for_metric,
                                                                                                             service_threshold_configs)

        operation, existing_monitor_id = self.check_if_create_or_edit_monitor(for_metric, service_threshold_configs, generated_formula)

        if operation == "create":
            self.create_monitor(generated_tags, generated_monitor_name, generated_formula)
        elif operation == "edit":
            self.edit_monitor(existing_monitor_id, generated_formula)
        else:
            logging.info("No changes need for Monitor: {} for mertic: {}".format(service_threshold_configs['apm_name'],
                                                                                 for_metric))
    def get_threshold_values(self, service_threshold_configs):
        service_name = service_threshold_configs[1]['apm_name']
        threshold_response_time = str(service_threshold_configs[1]['response_time'])
        threshold_throughput = str(service_threshold_configs[1]['throughput'])
        threshold_error_rate = str(service_threshold_configs[1]['error_rate'])
        return {'apm_name': service_name, 'response-time': threshold_response_time,
                'throughput': threshold_throughput, 'error-rate': threshold_error_rate}

    def configure_monitors(self):

        for application_config in self.application_monitors_configs.items():
            service_threshold_configs = self.get_threshold_values(application_config)
            self.create_or_edit_monitor(for_metric="response-time", service_threshold_configs=service_threshold_configs)
            self.create_or_edit_monitor(for_metric="throughput", service_threshold_configs=service_threshold_configs)
            self.create_or_edit_monitor(for_metric="error-rate", service_threshold_configs=service_threshold_configs)

def setup_argparser():

    parser = argparse.ArgumentParser(description="Pass in api key and application key of DD to create/edit monitors based on values in application_monitors_configs.yaml")

    parser.add_argument('--api_key',
                        required=True)

    parser.add_argument('--application_key',
                        required=True)

    return parser.parse_args()

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(asctime)s - %(message)s',
                        datefmt='%d-%b-%y %H:%M')
def main():
    # Setup argparser & Logging
    args = setup_argparser()
    setup_logging()

    # Start Monitor Configurator Service and load monitor configuration yaml
    monitors_configurator = DDMonitorsService(api_key=args.api_key, application_key=args.application_key)

    # Create New or re-configure existing Monitors
    monitors_configurator.configure_monitors()


if __name__ == '__main__':
    main()
