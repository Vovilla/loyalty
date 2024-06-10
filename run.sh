#!/bin/bash


if [ $# -eq 0 ]
  then
    reflex run

else
    reflex run --frontend-port $1
fi
