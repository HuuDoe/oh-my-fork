#!/bin/bash
SEEN=/tmp/omf/gh_seen.txt; touch $SEEN
for i in $(seq 1 300); do
  gh api "repos/HuuDoe/oh-my-fork/commits/a44be178152a70080e5715d88bab90e85714ffe7/comments" --jq '.[].body' 2>/dev/null | while IFS= read -r line; do
    key=$(echo "$line" | md5sum | cut -c1-8)
    grep -qxF "$key" $SEEN || { echo "$key" >> $SEEN; echo "COMMENT: ${line:0:80}"; }
  done
  sleep 6
done
