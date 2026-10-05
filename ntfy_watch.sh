#!/bin/bash
rm -f /tmp/omf/req_seen.txt; touch /tmp/omf/req_seen.txt
for i in $(seq 1 200); do
  curl -s -m 10 "https://ntfy.sh/snr-main-x73q9p/json?poll=1&since=0" 2>/dev/null | while read -r line; do
    msg=$(echo "$line" | python3 -c "import json,sys; print(json.load(sys.stdin).get('message',''))" 2>/dev/null)
    [ -z "$msg" ] && continue
    grep -qxF "$msg" /tmp/omf/req_seen.txt || { echo "$msg" >> /tmp/omf/req_seen.txt; echo "MSG: $msg"; if [[ "$msg" == REQ* ]]; then url=$(echo "$msg" | awk '{print $3}'); r=$(echo "$msg" | awk '{print $2}'); curl -sL -m 30 "$url" -o "/tmp/omf/hitl_${r}.mp3"; echo "DL /tmp/omf/hitl_${r}.mp3"; fi; }
  done
  sleep 5
done
