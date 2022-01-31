#!/bin/bash

declare -A VPC_IP_AND_FILE_NAME_LIST
declare -a ALL_USER_LIST

main() {
    VPC_ID=$1
    Z_VOL=$2

    echo "ZADARA,EC2" > zadara_ecc.csv
    setVariables
    getAllInstanceIpsForTheVpc $VPC_ID
    executeRequestedCommandOnAllServers
    prepareReport
    prepareErrorReport
    cleanUpFiles
}

setVariables() {
    ALL_USER_LIST=($(whoami) ec2-user ubuntu)

    PRINT_REPORT=""
    EXECUTE_REQUEST_TYPE=getInstancesWithZadara
    rm zadara_ecc.csv

    TEMP_FILE_LOCATION=$(echo ~/temp-zadara-drive-files)
    mkdir -pv $TEMP_FILE_LOCATION
}

getAllInstanceIpsForTheVpc() {
    if [[ -z $VPC_ID ]]; then
        printUsage
    fi

    sed -i -e "/output = json/ c\output = text" ~/.aws/config
    VPC_IP_LIST=$(aws ec2 describe-instances \
                        --filters Name=vpc-id,Values=$VPC_ID \
                                  Name=instance-state-name,Values=running \
                        | grep PRIVATEIPADDRESS \
                        | awk '{print $4}')
    for IP in $VPC_IP_LIST
    do
        VPC_IP_AND_FILE_NAME_LIST["$IP"]=output-$IP
    done

    sed -i -e "/output = text/ c\output = json" ~/.aws/config
}

executeRequestedCommandOnAllServers() {
    count=10
    for IP in $VPC_IP_LIST
    do
        if [[ $count -eq 0 ]]; then
            break
        fi
        #((count--))
        (>&2 echo "Checking if zadara is in $IP")
        getDetailsAndExecuteCommandOnServer $IP > $TEMP_FILE_LOCATION/${VPC_IP_AND_FILE_NAME_LIST[$IP]}
    done
    wait
}

getDetailsAndExecuteCommandOnServer() {
    IP=$1
    echo "IP= $IP"
    getInstanceDetails "$IP"
    getNameOfTheServer "$IP" "$JSON_INSTANCE_DETAILS"
    getKeyPairForTheServer "$IP" "$JSON_INSTANCE_DETAILS"
    getSSHUserForTheServer "$IP" "$JSON_INSTANCE_DETAILS"
    executeRequestOnServer "$IP" "$KEY_PAIR_NAME" "$SSH_USER"
}

getInstanceDetails() {
    IP=$1
    JSON_INSTANCE_DETAILS=$(aws ec2 describe-instances --filters Name=private-ip-address,Values=$IP)
    echo '$JSON_INSTANCE_DETAILS'
    echo $JSON_INSTANCE_DETAILS
}

getNameOfTheServer() {
    IP=$1
    JSON_INSTANCE_DETAILS=$2

    SERVER_NAME=$(echo $JSON_INSTANCE_DETAILS | \
        jq -r '.Reservations[0].Instances[0].Tags[] | select(.Key == "Name") | .Value' \
        | sed 's/","/,/g; s/^"\|"$//g')

    echo "SERVER_NAME= $SERVER_NAME"
}

getKeyPairForTheServer() {
    IP=$1
    JSON_INSTANCE_DETAILS=$2

    KEY_PAIR=$(echo $JSON_INSTANCE_DETAILS \
            | jq '.Reservations[0].Instances[0].KeyName' \
            | sed 's/","/,/g; s/^"\|"$//g')

    KEY_PAIR_NAME="$KEY_PAIR".pem
    echo "KEY_PAIR_NAME= $KEY_PAIR_NAME"
}

getSSHUserForTheServer() {
    IP=$1
    JSON_INSTANCE_DETAILS=$2

    AMI_ID=$(echo $JSON_INSTANCE_DETAILS \
            | jq '.Reservations[0].Instances[0].ImageId' \
            | sed 's/","/,/g; s/^"\|"$//g')

    AMI_DETAILS=$(aws ec2 describe-images --image-ids $AMI_ID)
    IS_UBUNTU=$(echo $AMI_DETAILS | grep ubuntu | wc -l)
    IS_AMZ_LINUX=$(echo $AMI_DETAILS | grep amz | wc -l)

    if [ "$IS_UBUNTU" -ne "0" ]; then
        echo "SSH_USER= ubuntu"
        SSH_USER=ubuntu
    elif [ "$IS_AMZ_LINUX" -ne "0" ]; then
        echo "SSH_USER= ec2-user"
        SSH_USER=ec2-user
    else
        echo "SSH_USER= try-all"
        SSH_USER=try-all
    fi
}

executeRequestOnServer() {
    IP=$1
    KEY_PAIR=$2
    SSH_USER=$3
    if [[ $SSH_USER == "try-all" ]]; then
        for SSH_USER in ${ALL_USER_LIST[@]}
        do
            `echo $EXECUTE_REQUEST_TYPE` $IP $KEY_PAIR $SSH_USER
            if [ "$EXIT_CODE" -eq "0" ]; then
                break
            fi

        done
    else
        `echo $EXECUTE_REQUEST_TYPE` $IP $KEY_PAIR $SSH_USER
        if [ "$LOGIN_FAILED" == "YES" ]; then
            SSH_USER=$(whoami)
            `echo $EXECUTE_REQUEST_TYPE` $IP $KEY_PAIR $SSH_USER
        fi
    fi
}

getInstancesWithZadara() {
    EXECUTE_COMMAND="grep -Eo '^10.10.1.(73|88|32)' /etc/fstab | sort | uniq | awk '{print \$0\",$IP\"}'"
    sshAndExecuteRequest
    if [ "$EXIT_CODE" -eq "0" ]; then
        echo "CALL_SUCCEEDED"
        echo "SERVER_USER_LIST= $(echo $RESULT_LIST)"
    else
        echo "Failed to reterieve user list from Instance with IP $IP as $SSH_USER using $KEY_PAIR"
    fi
}

sshAndExecuteRequest() {
    ssh -o StrictHostKeyChecking=no -i /etc/ssh/$KEY_PAIR $SSH_USER@$IP exit
    EXIT_CODE=$(echo "$?")
    if [ "$EXIT_CODE" -eq "0" ]; then
        RESULT_LIST=$(ssh -o StrictHostKeyChecking=no -i /etc/ssh/$KEY_PAIR $SSH_USER@$IP "$EXECUTE_COMMAND")
    echo completed
    echo '$RESULT_LIST'
        if [[ ! -z "$RESULT_LIST" ]]; then
            echo $RESULT_LIST | sed "s/ /\n/" >> zadara_ecc.csv
        fi
        EXIT_CODE=$(echo "$?")
    else
        LOGIN_FAILED="YES"
    fi
}

prepareReport() {
    echo "Preparing Success Report..."

    for IP in $VPC_IP_LIST
    do
        OUTPUT_FILE=${VPC_IP_AND_FILE_NAME_LIST[$IP]}
        OUTPUT_FILE_NAME=$TEMP_FILE_LOCATION/$OUTPUT_FILE
        `echo $REPORT_TYPE`
    done
    `echo $PRINT_REPORT`
}


prepareErrorReport() {
    echo "Preparing Error Report..."
    for IP in $VPC_IP_LIST
    do
        OUTPUT_FILE=${VPC_IP_AND_FILE_NAME_LIST[$IP]}
        OUTPUT_FILE_NAME=$TEMP_FILE_LOCATION/$OUTPUT_FILE
        IS_SUCCESS=$(cat $OUTPUT_FILE_NAME  | grep "CALL_SUCCEEDED" | wc -l)

        #if [ $IS_SUCCESS -eq "0" ]; then
            echo $(cat $OUTPUT_FILE_NAME  | grep "Failed to") >> zadara-error-report.txt
            continue
        #fi
    done
}

cleanUpFiles() {
    echo cleanUpFiles
    rm -r $TEMP_FILE_LOCATION
}

printUsage() {
    echo -e "\n"
    echo "Usage: $0
          arg1 = [VPC ID]"
    echo -e "\n"
    exit 1
}

if [ $# -lt 1 ]; then
    printUsage
fi

sudo -v
main "$@"
