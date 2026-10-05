#!/bin/bash
SEEN=/tmp/omf/seen.txt; touch $SEEN
for i in $(seq 1 60); do
  gh run view 37308160517 --repo HuuDoe/oh-my-fork --log 2>/dev/null | grep -oE "(HITL_KEY|AWAIT) [^ ]+ ?[^ ]*" | while read -r line; do
    grep -qxF "$line" $SEEN || { echo "$line" >> $SEEN; echo "NEW: $line"; url=$(echo "$line" | grep -oE 'https?://[^ ]+'); [ -n "$url" ] && curl -sL -m 30 "$url" -o "/tmp/omf/hitl_$(echo $line | awk '{print $2}').mp3" && echo "DOWNLOADED $url"; }
  done
  sleep 15
done
