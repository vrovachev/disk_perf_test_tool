#!/bin/bash

while [[ $# > 1 ]]
do
key="$1"

case $key in
    test)
    TEST="$2"
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

# discover url. take rabbit creads from nova.conf
rabbit_username=`cat /etc/nova/nova.conf | grep rabbit_user | grep -v "#" | awk '{print $3}'`
rabbit_password=`cat /etc/nova/nova.conf | grep rabbit_pass | grep -v "#" | awk '{print $3}'`
rabbit_hosts=`cat /etc/nova/nova.conf | grep rabbit_hosts | grep -v "#" | sed 's/rabbit_hosts//g;s/,//g;s/=//g;'`
rabbit_port=`cat /etc/nova/nova.conf | grep rabbit_port | grep -v "#" | awk '{print $3}'`

if [ "$TEST" = "pika" ]
 then
   url="pika://"
   for host in $rabbit_hosts;
    do
     url="$url$rabbit_username:$rabbit_password@$host,"
    done
fi

if [ "$TEST" = "rabbit" ]
 then
   url="rabbit://"
   for host in $rabbit_hosts;
    do
     url="$url$rabbit_username:$rabbit_password@$host,"
    done
fi

if [ "$TEST" = "zmq" ]
 then
   url="zmq://"
   for host in $rabbit_hosts;
    do
     url="$url$host:26379,"
    done
fi

mkdir -p "/tmp/testlogs/$TEST"
SERVER_LOG_FILE="/tmp/testlogs/$TEST/server-"
CLIENT_LOG_FILE="/tmp/testlogs/$TEST/client"

cd /tmp/oslo.messaging/tools
source /tmp/venv/bin/activate

# retrieve host ip
host=`ip a | grep 10.20 | awk '{print $2}' | sed 's/\//\ /g' | awk '{print $1}'`

# if zmq - start broker
if [ "$TEST" = "zmq" ]
then
    echo "[matchmaker_redis]" > /tmp/zmq.conf
    echo "$url" > /tmp/zmq.conf
    oslo-messaging-zmq-broker --config-file /tmp/zmq.conf &> /tmp/broker.log &
fi

# generate topics
hostname=`hostname -s`
seq_topics=`seq "$NUM_TOPICS"`
topics=`for i in $seq_topics; do echo "becnhmark_topic_$i"; done`
topics_arr=($topics)

servers=`cat /etc/hosts | grep node- |grep -v node-39| grep -v node-40| grep -v node-25| grep -v messaging| awk '{print $3}'`
servers_arr=($servers)
IFS=,
targets=`eval echo {"${topics_arr[*]}"}.{"${servers_arr[*]}"}`
unset IFS
# start servers
for i in `seq "$SERVERS"`;
 do
 python simulator.py $CONF_FILE_OPT  --url "$url" -tp "${topics_arr[$((i % NUM_TOPICS))]}" -s $hostname -l $((TIMEOUT + 60)) rpc-server &> "$SERVER_LOG_FILE$i" &
 done

# wait for all server processes to start
while [ "$(ps aux | grep simulator.py | grep -v grep | wc -l)" -ne  "$SERVERS" ]
do
sleep 1
done

# start client
python simulator.py $CONF_FILE_OPT -l "$TIMEOUT"  -tg $targets --url "$url" rpc-client --timeout 60 -p "$CLIENTS" -m 100 &> "$CLIENT_LOG_FILE" &

# wait for all simulator processes to finish
while [ "$(ps aux | grep simulator.py | grep -v grep)" ]
do
sleep 1
done

# log total sent
cat "/tmp/testlogs/$TEST/client" | grep "messages were sent" |  grep -o '[0-9,.]\+' | head -2

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
