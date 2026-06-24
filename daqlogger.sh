#!/bin/bash

folder=$(ls -1 runs | sort -V | tail -n 1)

echo runs/$folder/log/*${1}*

tail -f runs/$folder/log/*${1}*

