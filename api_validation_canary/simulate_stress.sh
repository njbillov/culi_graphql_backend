#!/bin/bash

# Accept first arg as number of workers, default to 3 if not specified
num_workers=${1:-3}
num_iterations=${2:-100}
echo "Running load tests with $num_workers concurrent workers for $num_iterations iterations."

simulate_load(){
    echo "Running validation on the backend servers"
    prefix=$(date +'%Y/%m/%d')
    mkdir -p $(date +'%Y/%m')
    python3 api_validator.py >> ${prefix}.log   
    sleep 0.1
}


# Simulate requests infinitely if a number of iterations is not specified
simulate_requests(){
    for (( i=1; i <= $num_iterations; i++ ))
    do
        simulate_load
    done
}


for (( i=1; i <=$num_workers ; i++ ))
do
    simulate_requests &
    sleep 0.1
done


wait

echo "All load simulation completed"