#!/bin/sh

curl -s \
     -X "POST" "http://localhost:8083/connectors/" \
     -H "Content-Type: application/json" \
  --data '{ 
  "name": "hdfs-sink-phrases", 
   "config": { 
     "connector.class": "io.confluent.connect.hdfs3.Hdfs3SinkConnector", 
     "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
     "partition.duration.ms": 1800000,
     "path.format": "YYYYMMdd_HHmm",
     "timestamp.extractor":"Record",
     "confluent.topic.bootstrap.servers":"assembler.broker:9092",
     "tasks.max": "1", 
     "topics": "phrases", 
     "hdfs.url": "hdfs://assembler.hadoop.namenode:9000", 
     "flush.size": "3", 
     "locale": "en",
     "timezone": "UTC",
     "topics.dir": "/phrases/1_sink",
     "logs.dir": "/phrases/1_sink/logs",
     "name": "hdfs-sink-phrases" 
 } }'

