DOCKER_NETWORK = autocomplete_default
ENV_FILE = assembler/hadoop/hadoop.env

run:
	docker-compose up --build --scale distributor.backend=8 --scale distributor.frontend=2 --scale assembler.collector=2 && docker-compose down

do_mapreduce_tasks:
	docker build -t lopespm/mapreduce-tasks ./assembler/hadoop/mapreduce-tasks
	docker run --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} lopespm/mapreduce-tasks

setup:
	docker build -t lopespm/hadoop-base ./assembler/hadoop/base	

	while [[ "$$(echo "stat" | nc localhost 2181 | grep Mode)" != "Mode: standalone" ]] ; do \
	    echo "Waiting for zookeeper to come online" ; \
	    sleep 2 ; \
	done

	docker exec zookeeper ./bin/zkCli.sh -server localhost:2181 create /phrases ""
	docker exec zookeeper ./bin/zkCli.sh -server localhost:2181 create /phrases/assembler ""
	docker exec zookeeper ./bin/zkCli.sh -server localhost:2181 create /phrases/assembler/last_built_target ""

	docker exec zookeeper ./bin/zkCli.sh -server localhost:2181 create /phrases/distributor ""
	docker exec zookeeper ./bin/zkCli.sh -server localhost:2181 create /phrases/distributor/current_target ""
	docker exec zookeeper ./bin/zkCli.sh -server localhost:2181 create /phrases/distributor/next_target ""

	while [[ $$(curl -s -o /dev/null -w %{http_code} http://localhost:9870/) -ne "200" ]] ; do \
	    echo "Waiting for hadoop's namenode to come online" ; \
	    sleep 2 ; \
	done

	docker run --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} lopespm/hadoop-base hadoop fs -mkdir -p /phrases/1_sink/
	docker run --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} lopespm/hadoop-base hadoop fs -mkdir -p /phrases/2_with_weight/
	docker run --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} lopespm/hadoop-base hadoop fs -mkdir -p /phrases/3_with_weight_merged/
	docker run --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} lopespm/hadoop-base hadoop fs -mkdir -p /phrases/4_with_weight_ordered/
	docker run --network ${DOCKER_NETWORK} --env-file ${ENV_FILE} lopespm/hadoop-base hadoop fs -mkdir -p /phrases/5_tries/

populate_search:
	echo "Populating search phrases to the collector"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=awesome"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=ball"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=bank"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=car"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=car electric"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=dog"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=epsilon"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=far"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=furthest"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=games"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=games online"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=hello"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=hello world"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=irk"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=json"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=kangaroo animal"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=lars"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=make"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=mod"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=mod chip"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=modern style"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=nay"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=oat meal"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=quorum"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=quota"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=raspberry pi"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=saturn"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=turtles"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=union"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=vpn"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=wonderful"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=xbox"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=xtend"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=youtube music"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=zookeeper"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=zk"

	curl -X POST -G http://localhost/search --data-urlencode "phrase=hello world"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=hello"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=quorum"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=hello world"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=make"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=games online"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=super plus"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=weather"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=food near me"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=winter olympics"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=jupyter"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=popular searches"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=random phrase"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=jupyter"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=juniper"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=computer"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=calculator"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=car electric"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=modern style"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=measure"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=measure"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=unanimous"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=rainbow"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=system design"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=special"
	curl -X POST -G http://localhost/search --data-urlencode "phrase=mars"
