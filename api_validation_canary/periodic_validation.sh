#!/bin/bash

while :
do
    echo "Running validation on the backend servers"
    prefix=$(date +'%Y/%m/%d')
    mkdir -p $(date +'%Y/%m')
    python3 api_validator.py >> ${prefix}.log   
    sleep 900
done
