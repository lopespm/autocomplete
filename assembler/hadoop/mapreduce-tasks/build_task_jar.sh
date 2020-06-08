#!/bin/bash

# e.g. "PhrasesWithWeight"
TASKNAME=$1
echo $TASKNAME
cd /opt/hadoop/applications/${TASKNAME}
mkdir classes && CLASSPATH=".:../lib/*:$(hadoop classpath)" javac -d ./classes ${TASKNAME}.java
jar cf ${TASKNAME}.jar -C classes .