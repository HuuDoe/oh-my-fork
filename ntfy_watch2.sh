#!/bin/bash
SEEN=/tmp/omf/req_seen2.txt; touch $SEEN
for i in $(seq 1 300); do
  curl -s -m 10 "https://ntfy.sh/snr-main-x73q9p/json?poll=1&since=0" 2>/dev/null | while read -r line; do
    msg=$(echo "$line" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
    [ -z "$msg" ] && continue
    grep -qxF "$msg" $SEEN || echo "$msg" >> $SEEN && echo "NEW: $msg" || continue
    if [[ "$msg" == REQ* ]]; then
      r=$(echo "$msg" | awk '{print $2}'); url=$(echo "$msg" | awk '{print $3}')
      out="/tmp/omf/hitl_new_${r}.mp3"
      if [[ "$url" == *tmpfiles.org* ]]; then
        real=$(curl -sL -m 12 "$url" | grep -oE 'https://tmpfiles.org/dl/[0-9]+\.[a-f0-9]+/[^"]+mp3' | head -1)
        [ -n "$real" ] && curl -sL -m 20 "$real" -o "$out"
      else
        curl -sL -m 20 "$url" -o "$out"
      fi
      file "$out" | grep -qi audio && echo "GOT_MP3 $out" || echo "BAD_MP3 $out"
    fi
  done
  sleep 4
done
