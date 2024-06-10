#!/bin/bash

reflex db init
reflex db makemigrations
reflex db migrate