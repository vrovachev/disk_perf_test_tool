#!/bin/bash

while [[ $# > 1 ]]
do
key="$1"

case $key in
    url)
    URL="$2"
    shift
    ;;
    timeout)
    TIMEOUT="$2"
    shift
    ;;
    clients)
    CLIENTS="$2"
    shift
    ;;
    servers)
    SERVERS="$2"
    shift
    ;;
    num_topics)
    NUM_TOPICS="$2"
    shift
    ;;
    *)
    echo "Unknown option $key"
    exit 1
    ;;
esac
shift
done


OMGPATH=/tmp
mkdir -p "/tmp/testlogs"
SERVER_LOG_FILE=/tmp/testlogs/server-
CLIENT_LOG_FILE=/tmp/testlogs/client

cd "$OMGPATH/oslo.messaging/tools"
source "$OMGPATH/venv/bin/activate"

topics=`python -c "import petname; print ' '.join([petname.Generate(3, '_') for i in range($NUM_TOPICS)])"`
topics_arr=($topics)

for i in `seq "$SERVERS"`;
 do
 python simulator.py --url "$URL" -tp "${topics_arr[$((i % NUM_TOPICS))]}" -l $((TIMEOUT + 5)) rpc-server &> "$SERVER_LOG_FILE$i" &
 done

python simulator.py  -l "$TIMEOUT" -tp $topics --url "$URL" rpc-client -p "$CLIENTS" -m 100 &> "$CLIENT_LOG_FILE" &

wait

while `ps aux | grep simulator.py | grep -v grep`
do
sleep 1
done

# grep total sent

cat /tmp/testlogs/client | grep "messages were sent" |  grep -o '[0-9,.]\+' | head -2

# grep total received
for i in `seq "$SERVERS"`;
 do
 cat "$SERVER_LOG_FILE$i" | grep "Received total" | grep -o '[0-9,.]\+';
 done
