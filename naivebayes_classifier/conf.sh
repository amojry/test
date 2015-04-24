#!/bin/bash
set -o nounset
set -e 
[[ -a model ]] || mkdir model
[[ -a data ]] || mkdir data
[[ -a corpus ]] || mkdir corpus
echo '' > model/N
echo '' > model/C
echo '' > model/D
echo '' > model/TF
echo '' > model/DF
echo '' > model/W
