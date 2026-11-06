#!/usr/bin/env bash
# Build the handbook into public/: one HTML page per docs/*.md, plus an index.
set -euo pipefail

rm -rf public
mkdir -p public

{
    printf '<!doctype html>\n<title>Larkspur handbook</title>\n<ul>\n'
    for page in docs/*.md; do
        name=$(basename "$page" .md)
        printf '<li><a href="%s.html">%s</a></li>\n' "$name" "$name"
        {
            printf '<!doctype html>\n<title>%s</title>\n<pre>\n' "$name"
            cat "$page"
            printf '</pre>\n'
        } > "public/${name}.html"
    done
    printf '</ul>\n'
} > public/index.html

echo "build: $(ls public | wc -l) file(s) in public/"
