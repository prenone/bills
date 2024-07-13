#!/bin/bash

rm -f physcraft-bills.tar
docker build -t physcraft-bills .
docker save -o physcraft_bills.tar physcraft-bills