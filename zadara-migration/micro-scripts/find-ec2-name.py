import csv
import boto3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M')
client = boto3.client('ec2')

with open('zadara_ecc.csv', mode='r') as ec2_list, open('temp.csv', mode='w') as temp:

    csv_reader = csv.DictReader(ec2_list)
    csv_writer = csv.DictWriter(temp, fieldnames=["ZADARA", "EC2", "INSTANCE_NAME"])
    csv_writer.writeheader()
    for row in csv_reader:
        ip = row['EC2']
        instance_details = client.describe_instances(Filters=[{'Name': 'private-ip-address', 'Values': [ip]}])
        try:
            instance_id = instance_details['Reservations'][0]['Instances'][0]['InstanceId']
        except:
            logging.info("Couldn't not find name for instance {}".format(row['EC2']))
            csv_writer.writerow({'ZADARA': row['ZADARA'], 'EC2': row['EC2'], 'INSTANCE_NAME': 'NO_NAME'})
            continue
        tags = client.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [instance_id]}])
        instance_name = tags['Tags'][0]['Value']
        logging.info("Zadara mount point: {} | EC2 IP: {} | EC2 Name: {}".format(row['ZADARA'], row['EC2'], instance_name))
        csv_writer.writerow({'ZADARA': row['ZADARA'], 'EC2': row['EC2'], 'INSTANCE_NAME': instance_name})
    os.rename("temp.csv", "zadara_ec2_name.csv")
    logging.info("Check zadara_ec2.csv for zadara-ec2 list")

