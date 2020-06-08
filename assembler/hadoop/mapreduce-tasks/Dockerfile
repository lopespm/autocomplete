FROM bde2020/hadoop-base:2.0.0-hadoop3.2.1-java8


ARG AVROLIBPATH=/opt/hadoop/applications/lib/avro-tools-1.8.2.jar

COPY PhrasesWithWeight.java /opt/hadoop/applications/PhrasesWithWeight/PhrasesWithWeight.java
COPY PhrasesWithWeightMerged.java /opt/hadoop/applications/PhrasesWithWeightMerged/PhrasesWithWeightMerged.java
COPY PhrasesWithWeightOrdered.java /opt/hadoop/applications/PhrasesWithWeightOrdered/PhrasesWithWeightOrdered.java

COPY lib/avro-tools-1.8.2.jar /opt/hadoop/applications/lib/avro-tools-1.8.2.jar
COPY phrases.avsc /opt/hadoop/applications/schema/phrases.avsc

RUN cd /opt/hadoop/applications/schema && java -jar $AVROLIBPATH compile schema phrases.avsc /opt/hadoop/applications/PhrasesWithWeight/

COPY build_task_jar.sh /opt/hadoop/applications/build_task_jar.sh
COPY do_tasks.sh /opt/hadoop/applications/do_tasks.sh
RUN chmod a+x /opt/hadoop/applications/build_task_jar.sh
RUN chmod a+x /opt/hadoop/applications/do_tasks.sh

RUN cd /opt/hadoop/applications/ && ./build_task_jar.sh "PhrasesWithWeight"
RUN cd /opt/hadoop/applications/ && ./build_task_jar.sh "PhrasesWithWeightMerged"
RUN cd /opt/hadoop/applications/ && ./build_task_jar.sh "PhrasesWithWeightOrdered"

# Download zookeeper (to access the remote cli)
RUN curl https://mirrors.up.pt/pub/apache/zookeeper/zookeeper-3.6.1/apache-zookeeper-3.6.1-bin.tar.gz -o /tmp/apache-zookeeper-3.6.1-bin.tar.gz
RUN tar -xf /tmp/apache-zookeeper-3.6.1-bin.tar.gz -C /tmp/
RUN mv /tmp/apache-zookeeper-3.6.1-bin /zookeeper
RUN rm /tmp/apache-zookeeper-3.6.1-bin.tar.gz


CMD ["/opt/hadoop/applications/do_tasks.sh"]
