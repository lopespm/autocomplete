#!/bin/bash

TARGET_ID=$(date +%Y%m%d_%H%M)
AVROLIB_PATH="/opt/hadoop/applications/lib/avro-tools-1.8.2.jar"
LIBJARS="${AVROLIB_PATH}"
MAX_NUMBER_OF_INPUT_FOLDERS="3"

# Wait for phrases
echo "Checking if /phrases/1_sink/phrases/ exists.."
while ! $(hadoop fs -test -d "/phrases/1_sink/phrases/") ; do echo "Waiting for folder /phrases/1_sink/phrases/ to be created by kafka connect. Please wait.."; done
echo "Checking for contents in /phrases/1_sink/phrases/.."
while [[ $(hadoop fs -ls /phrases/1_sink/phrases/ | sed 1,1d) == "" ]] ; do echo "Waiting for kafka connect to populate /phrases/1_sink/phrases/*. Please wait.."; done

# PhrasesWithWeight
hadoop fs -mkdir -p /phrases/2_with_weight/${TARGET_ID}/

INPUT_FOLDERS=`hadoop fs -ls /phrases/1_sink/phrases/ | sed 1,1d | sort -r -k8 | awk '{print \$8}' | head -${MAX_NUMBER_OF_INPUT_FOLDERS} | sort`
echo "${INPUT_FOLDERS}"
TASKNAME="PhrasesWithWeight"
CLASS_TO_RUN="${TASKNAME}"
JAR_FILEPATH="/opt/hadoop/applications/${TASKNAME}/${TASKNAME}.jar"
cd "/opt/hadoop/applications/${TASKNAME}"
base_weight=1 
for input_folder in ${INPUT_FOLDERS} ; do
	echo "Processing input: " $input_folder ;
	echo "base_weight: " $base_weight ;

	HADOOP_CLASSPATH="${AVROLIB_PATH}" $HADOOP_HOME/bin/hadoop jar ${JAR_FILEPATH} ${CLASS_TO_RUN} -libjars ${LIBJARS} ${input_folder} /phrases/+tmp ${base_weight} ;
	hdfs dfs -cat /phrases/+tmp/* ;
	hdfs dfs -mv /phrases/+tmp/* /phrases/2_with_weight/${TARGET_ID}/ ;
	hdfs dfs -rm -r /phrases/+tmp/ ;

	base_weight=$(( 10*base_weight ));
done


# PhrasesWithWeightMerged
TASKNAME="PhrasesWithWeightMerged"
CLASS_TO_RUN="${TASKNAME}"
JAR_FILEPATH="/opt/hadoop/applications/${TASKNAME}/${TASKNAME}.jar"
cd "/opt/hadoop/applications/${TASKNAME}"
HADOOP_CLASSPATH="${AVROLIB_PATH}" $HADOOP_HOME/bin/hadoop jar ${JAR_FILEPATH} ${CLASS_TO_RUN} -libjars ${LIBJARS} /phrases/2_with_weight/${TARGET_ID} /phrases/3_with_weight_merged/${TARGET_ID} 0
hdfs dfs -cat /phrases/3_with_weight_merged/${TARGET_ID}/*


# PhrasesWithWeightOrdered
TASKNAME="PhrasesWithWeightOrdered"
CLASS_TO_RUN="${TASKNAME}"
JAR_FILEPATH="/opt/hadoop/applications/${TASKNAME}/${TASKNAME}.jar"
cd "/opt/hadoop/applications/${TASKNAME}"
HADOOP_CLASSPATH="${AVROLIB_PATH}" $HADOOP_HOME/bin/hadoop jar ${JAR_FILEPATH} ${CLASS_TO_RUN} -libjars ${LIBJARS} /phrases/3_with_weight_merged/${TARGET_ID} /phrases/4_with_weight_ordered/${TARGET_ID} 0
hdfs dfs -cat /phrases/4_with_weight_ordered/${TARGET_ID}/*


# Register in zookeeper
cd /zookeeper/bin
./zkCli.sh -server zookeeper:2181 set /phrases/assembler/last_built_target ${TARGET_ID}