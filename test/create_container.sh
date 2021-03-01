#!/usr/bin/env bash
#build container

MAJOR=0
MINOR=1

#cp ../arse.py .
cp ../config.json .
#cp ../sample_input.xlsx input.xlsx

docker build -t test:$MAJOR.$MINOR . && docker run -p 5000:5000 --rm --name test test:$MAJOR.$MINOR && docker image prune -f
