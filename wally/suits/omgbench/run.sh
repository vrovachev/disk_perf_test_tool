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
    start_broker)
    START_BROKER="$2"
    shift
    ;;
    zmq_host)
    ZMQ_HOST="$2"
    shift
    ;;
    zmq_password)
    ZMQ_PASS="$2"
    shift
    ;;
    zmq_port)
    ZMQ_PORT="$2"
    shift
    ;;
    *)
    echo "Unknown option $key"
    exit 1
    ;;
esac
shift
done

test=${URL%://*}
mkdir -p "/tmp/testlogs/$test"
SERVER_LOG_FILE="/tmp/testlogs/$test/server-"
CLIENT_LOG_FILE="/tmp/testlogs/$test/client"

cd /tmp/oslo.messaging/tools
source /tmp/venv/bin/activate

# retrieve host ip
host=`ip a | grep 10.20 | awk '{print $2}' | sed 's/\//\ /g' | awk '{print $1}'`

# if zmq - start broker
if [[ "$START_BROKER" ]]
then
    cat > /tmp/zmq.conf <<EOF
[DEFAULT]
rpc_backend=zmq
rpc_zmq_matchmaker=redis
[matchmaker_redis]
port=${ZMQ_PORT:-6379}
host=${ZMQ_HOST:-localhost}
password=${ZMQ_PASS:-''}
EOF
    oslo-messaging-zmq-broker --config-file /tmp/zmq.conf &> /tmp/broker.log
    CONF_FILE_OPT="--config-file /tmp/zmq.conf"
fi

# generate topics
seq_topics=`seq "$NUM_TOPICS"`
topics=`for i in $seq_topics; do echo "becnhmark_topic_$i"; done`
topics_arr=($topics)

hostname=`hostname`
# start servers
for i in `seq "$SERVERS"`;
 do
 python simulator.py $CONF_FILE_OPT -d True --url "$URL" -tp "${topics_arr[$((i % NUM_TOPICS))]}" -s $hostname -l $((TIMEOUT + 20)) rpc-server &> "$SERVER_LOG_FILE$i" &
 done

# wait for all server processes to start
while [ "$(ps aux | grep simulator.py | grep -v grep | wc -l)" -ne  "$SERVERS" ]
do
sleep 1
done

# start client
python simulator.py $CONF_FILE_OPT -d True -l "$TIMEOUT" -tp $topics -s $hostname --url "$URL" rpc-client -p "$CLIENTS" -m 100 &> "$CLIENT_LOG_FILE" &

# wait for all simulator processes to finish
while [ "$(ps aux | grep simulator.py | grep -v grep)" ]
do
sleep 1
done

# log total sent
cat "/tmp/testlogs/$test/client" | grep "messages were sent" |  grep -o '[0-9,.]\+' | head -2

# log total received
for i in `seq "$SERVERS"`;
 do
 cat "$SERVER_LOG_FILE$i" | grep "Received total" | grep -o '[0-9,.]\+';
 done

# kill zmq-broker process
for p in `ps aux | grep zmq-broker | grep -v grep | awk '{print $2}'`;
do
kill "$p"
done
