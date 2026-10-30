#!/usr/bin/env bash
# Merge every data/*.csv into snapshot/all.csv, header once, rows sorted.
set -euo pipefail

mkdir -p snapshot
{
    echo "region,day,orders"
    tail -q -n +2 data/*.csv | sort
} > snapshot/all.csv
