#!/bin/bash

source zadara_efs_map.data

main() {
    backupFStab
    replaceMountInFStab
    remountAllDrives
}

backupFStab() {
    sudo cp /etc/fstab /etc/fstab.zadara
}

replaceMountInFStab() {
    for ZADARA in "${!EFS_MAP[@]}";
    do
    zadaraMount=${ZADARA}
    efsMount=${EFS_MAP[$zadaraMount]}
    sed -i "s~$zadaraMount~$efsMount~" /etc/fstab
    done
    wait
    echo "Done swaping drives in /etc/fstab"
}

remountAllDrives(){
    sudo umount -a
    wait
    echo "Done unmounting old drives"
    sudo mount -a
    wait
    echo "Done mounting new drives"
}
main "$@"
