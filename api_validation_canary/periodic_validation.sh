#!/bin/bash

wait_time=${1:-900}

while :
do
    echo "Running validation on the backend servers"
    prefix=$(date +'%Y/%m/%d')
    mkdir -p $(date +'%Y/%m')
    python3 api_validator.py >> ${prefix}.log   
    sleep $wait_time
done

echo "All load simulation completed"