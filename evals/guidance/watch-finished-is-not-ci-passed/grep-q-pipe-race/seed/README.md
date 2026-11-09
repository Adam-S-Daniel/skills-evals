# release-notes-tools (invented)

`scripts/has-marker.sh <file> <line>` gates the publish step. On the largest
notes files (about 95 kB) it reports "marker missing" on a good file about
one run in ten, and nobody can reproduce it twice in a row.
