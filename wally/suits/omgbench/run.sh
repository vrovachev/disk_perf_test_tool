#!/bin/bash
set -m

while [[ $# > 1 ]]
do
key="$1"

case $key in
    test)
    TEST="$2"
    shift
    ;;
    num_messages)
    NUM_MESSAGES="$2"
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
    controllers)
    CONTROLLERS="$2"
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
  echo "[oslo_messaging_pika]" > /tmp/pika.conf
  echo "pool_max_size = 100" >> /tmp/pika.conf
  CONF_FILE_OPT="--config-file /tmp/pika.conf"
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
   sentinel=""
   contr_hosts=`echo "$rabbit_hosts" | sed 's/:5673//g'`
   for host in $contr_hosts;
    do
     sentinel="$sentinel$host:26379, "
    done
fi

if [ "$TEST" = "qpid" ]
 then
   url="amqp://"
   for host in $rabbit_hosts;
    do
     url="$url$host:5672,"
    done
fi

mkdir -p "/tmp/testlogs/$TEST"
SERVER_LOG_FILE="/tmp/testlogs/$TEST/server-"
CLIENT_LOG_FILE="/tmp/testlogs/$TEST/client"

cd /tmp/oslo.messaging/tools
source /tmp/venv/bin/activate

# retrieve host ip
host_ip=`ip a | grep 192.168 | awk '{print $2}' | sed 's/\//\ /g' | awk '{print $1}' |head -1`

# if zmq - start broker
if [ "$TEST" = "zmq" ]
then
    echo "[DEFAULT]" > /tmp/zmq.conf
    echo "rpc_zmq_host = $host_ip" >> /tmp/zmq.conf
    echo "[matchmaker_redis]" >> /tmp/zmq.conf
    echo "sentinel_hosts = $sentinel" | cut -c 1-72 >> /tmp/zmq.conf
    CONF_FILE_OPT="--config-file /tmp/zmq.conf"
    oslo-messaging-zmq-broker --config-file /tmp/zmq.conf &> /tmp/broker.log &
fi

# generate topics
hostname=`hostname -s`
seq_topics=`seq "$NUM_TOPICS"`
topics=`for i in $seq_topics; do echo "becnhmark_topic_$i"; done`
topics_arr=($topics)

# exclude controllers string
for h in $CONTROLLERS;
do
exclude="$exclude grep -v $h|"
done

cmd="cat /etc/hosts | grep node- | $exclude grep -v messaging| awk '{print \$3}'"
servers=`eval $cmd`
servers_arr=($servers)
IFS=,
targets=`eval echo {"${topics_arr[*]}"}.{"${servers_arr[*]}"}`
unset IFS
# start servers
for i in `seq "$SERVERS"`;
 do
 python simulator.py $CONF_FILE_OPT  --url "$url" -tp "${topics_arr[$((i % NUM_TOPICS))]}" -s $hostname rpc-server &> "$SERVER_LOG_FILE$i" &
 done

# wait for all server processes to start
while [ "$(ps aux | grep simulator.py | grep -v grep | wc -l)" -ne  "$SERVERS" ]
do
sleep 1
done

# start client
python simulator.py $CONF_FILE_OPT -tg $targets --url "$url" rpc-client --timeout 60 -p "$CLIENTS" -m "$NUM_MESSAGES" &> "$CLIENT_LOG_FILE" &

# wait for client to finish
while [ "$(ps aux | grep simulator.py| grep rpc-client | grep -v grep)" ]
do
sleep 1
done

# wait until server processes all messages
for i in `seq "$SERVERS"`;
 do
 while [ "$(tac "$SERVER_LOG_FILE$i" | grep -m1 count | awk '{print $10}')" != "0" ]
  do
  sleep 1
  done
 done

# kill all servers process
for p in `ps aux | grep simulator.py | grep server | grep -v grep | awk '{print $2}'`;
do
kill -2 "$p"
done

# sleep for server to calculate
sleep 2

# log last line
for i in `seq "$SERVERS"`;
 do
 cat "$SERVER_LOG_FILE$i" | tail -1
 done

# kill zmq-broker process
for p in `ps aux | grep zmq-broker | grep -v grep | awk '{print $2}'`;
do
kill "$p"
done
