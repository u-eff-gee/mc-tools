#!/usr/bin/env bash

function usage()
{
    echo -e """
Prints the material comment string, assuming that the material description line precedes its definition
and contains the word 'Material' - as is the case in CombLayer-generated input files.
"""

    echo "Usage:" $(basename $0) file.inp m
    echo "       m        - material name (number with or without the 'M' prefix)"
    echo "       file.inp - FLUKA input file"
};


if [ $# != 2 ]; then
    usage
    exit 1
fi

if [ ! -e $1 ]; then
    echo "Can't open file $1"
    exit 1
fi

inp=$1
mat=$2


[[ $mat != [Mm]* ]] && mat="M"$mat

cat $inp | sed 's/[[:blank:]]*$//' | grep -i -B 1 $mat$ #| grep Material
