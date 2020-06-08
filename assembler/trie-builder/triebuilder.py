from hdfs import InsecureClient
from kazoo.client import KazooClient, DataWatch
import requests
import pickle
import time
import logging
import os

from trie import Trie

PARTITIONS = ((None, 'mod'), ('mod', None))
ZK_ASSEMBLER_LAST_BUILT_TARGET = '/phrases/assembler/last_built_target'
ZK_NEXT_TARGET = '/phrases/distributor/next_target'


class HdfsClient:
	def __init__(self, namenode_host, datanode_host):
		self._namenode_host = namenode_host
		self._datanode_host = datanode_host
		self._client = InsecureClient(f'http://{self._namenode_host}:9870')
		self._logger = logging.getLogger(__name__)
		self._logger.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))
		ch = logging.StreamHandler()
		ch.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))
		self._logger.addHandler(ch)

	def list(self, path):
		return self._client.list(path) 

	def get_stream(self, hdfs_path):
		request_path = f'http://{self._datanode_host}:9864/webhdfs/v1{hdfs_path}?op=OPEN&namenoderpcaddress={self._namenode_host}:9000&offset=0'
		return HdfsClientGetStream(request_path)

	def upload_to_hdfs(self, local_path, remote_path):
		self._logger.info(f'Upload local path {local_path} to {remote_path}')
		with open(local_path, 'rb') as f:
			r = requests.put(f'http://{self._namenode_host}:9870/webhdfs/v1{remote_path}?op=CREATE&overwrite=true', data=f)
			self._logger.debug(f'Upload result {r.content}')

class HdfsStream:
	def __init__(self, requests_stream):
		self._requests_stream = requests_stream

	def iter_lines(self):
		return self._requests_stream.iter_lines()

class HdfsClientGetStream:
	def __init__(self, request_path):
		self._r = requests.get(request_path, stream=True)

	def __enter__(self):
		return self._r.__enter__()

	def __exit__(self, type, value, traceback):
		self._r.__exit__(type, value, traceback)


class TrieBuilder:
	def __init__(self):
		self._zk = KazooClient(hosts=f'{os.getenv("ZOOKEEPER_HOST")}:2181')
		self._hdfsClient = HdfsClient(os.getenv("HADOOP_NAMENODE_HOST"), os.getenv("HADOOP_DATANODE_HOST"))
		self._logger = logging.getLogger(__name__)
		self._logger.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))
		ch = logging.StreamHandler()
		ch.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))
		self._logger.addHandler(ch)

	def start(self):
		self._zk.start()
		datawatch_next_target = DataWatch(client=self._zk, path=ZK_ASSEMBLER_LAST_BUILT_TARGET, func=self._on_assembler_last_built_target_changed)

	def stop(self):
		self._zk.stop()

	def _on_assembler_last_built_target_changed(self, data, stat, event=None):
		self._logger.debug("_on_assembler_last_built_target_changed Data is %s" % data)
		if (data is None):
			return

		self.build(data.decode())

	def build_most_recent(self):
		try:
			available_targets = self._hdfsClient.list("/phrases/4_with_weight_ordered") 
			if (not available_targets):
				return False

			available_targets.sort(reverse=True)	
			target_id = available_targets[0]
			return self.build(target_id)
		except Exception as e:
   			self._logger.error(f'Could not build most recent', exc_info=e)

		return False

	def _is_already_built(self, target_id):
		if (self._zk.exists(ZK_NEXT_TARGET) is None):
			return False
		next_target_id = self._zk.get(ZK_NEXT_TARGET)[0].decode()
		return next_target_id == target_id


	def build(self, target_id):
		if (not target_id or self._is_already_built(target_id)):
			return False

		self._logger.info(self._hdfsClient.list("/phrases/4_with_weight_ordered/" + target_id))

		for start, end in PARTITIONS:
			self._logger.debug(f'start: {start}; end: {end}')

			trie = self._create_trie(target_id, start, end)

			trie_local_file_name = "trie.dat"
			pickle.dump(trie, open(trie_local_file_name, "wb"))

			trie_remote_hdfs_path = self._get_trie_remote_hdfs_path(target_id, start, end)
			self._hdfsClient.upload_to_hdfs(trie_local_file_name, trie_remote_hdfs_path)
			self._register_trie_zookeeper(target_id, start, end, trie_remote_hdfs_path)

		self._register_next_target_zookeeper(target_id)

		return True


	def _create_trie(self, target_id, start, end):
		trie = Trie()
		with self._hdfsClient.get_stream(f'/phrases/4_with_weight_ordered/{target_id}/part-r-00000') as stream:
			for line_bytes in stream.iter_lines():
				if (not line_bytes):
					continue
				phrase = line_bytes.decode("utf-8").split('\t', maxsplit=1)[1]
				if ((not start or phrase >= start) and (not end or phrase < end)):
					self._logger.debug(f'Adding phrase: {phrase} for partition {start}|{end}')
					trie.add_phrase(phrase)
		return trie

	def _start_end_representation(self, start, end):
		return f'{start if (start) else ""}|{end if (end) else ""}'

	def _get_trie_remote_hdfs_path(self, target_id, start, end):
		return f'/phrases/5_tries/{target_id}/{self._start_end_representation(start, end)}'

	def _register_next_target_zookeeper(self, target_id):
		base_zk_path = f'/phrases/distributor/next_target'
		self._zk.ensure_path(f'{base_zk_path}')
		self._zk.set(f'{base_zk_path}', target_id.encode())

	def _register_trie_zookeeper(self, target_id, start, end, trie_hdfs_path):
		base_zk_path = f'/phrases/distributor/{target_id}/partitions/{self._start_end_representation(start, end)}'
		self._zk.ensure_path(f'{base_zk_path}/trie_data_hdfs_path')
		self._zk.ensure_path(f'{base_zk_path}/nodes')
		self._zk.set(f'{base_zk_path}/trie_data_hdfs_path', trie_hdfs_path.encode())




if __name__ == '__main__':
	trie_builder = TrieBuilder()
	trie_builder.start()
	trie_builder.build_most_recent()

	while True:
	    time.sleep(5)