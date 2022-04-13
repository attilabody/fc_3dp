#!/bin/sh
#usage rezip.sh [-#] [filename]

unset compression

while [ $# != 0 ] ; do
    case $1 in
    -*)
       compression="$1"
       ;;
    *)
       inputfile="$1"
    esac
    shift
done

if [ -z "$compression" ]; then compression=-0; fi

if [ -z "$inputfile" ]; then 
    zipfile=$(mktemp -t rezip.zip.XXXXXXXX)
    cat >"$zipfile"
else
    zipfile=$(realpath "$inputfile")
fi

tmpdir=$(mktemp -d -t rezip.tmd.XXXXXXXX)

files=$(unzip -Z -1 "$zipfile")
unzip -qq -d "$tmpdir" "$zipfile"
cd "$tmpdir"
tmpfile=$(mktemp -u -t rezip.tmp.XXXXXXXX)
unzip -Z -1 "$curdir/$zipfile"| zip -qq -@ "$compression" "$tmpfile"

if [ -z "$inputfile" ] ; then
    rm "$zipfile"
    cat "$tmpfile"
    rm "$tmpfile"
else
    mv "$tmpfile" "$zipfile"
fi

rm -rf "$tmpdir"

