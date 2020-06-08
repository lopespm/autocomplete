from hdfs import InsecureClient
from kazoo.client import KazooClient, DataWatch

import os
import pickle
import socket
import logging
from apscheduler.schedulers.background import BackgroundScheduler

from trie import Trie


ZK_CURRENT_TARGET = '/phrases/distributor/current_target'
ZK_NEXT_TARGET = '/phrases/distributor/next_target'
NUMBER_NODES_PER_PARTITION = int(os.getenv("NUMBER_NODES_PER_PARTITION"))


class NodeInactiveError(Exception):
	pass

class HdfsClient:
	def __init__(self, namenode_host):
		self._client = InsecureClient(f'http://{namenode_host}:9870')

	def download(self, remote_hdfs_path, local_path):
		self._client.download(remote_hdfs_path, local_path, overwrite=True)

class Backend:
	def __init__(self):
		self._logger = logging.getLogger('gunicorn.error')

		self._zk = KazooClient(hosts=f'{os.getenv("ZOOKEEPER_HOST")}:2181')
		self._hdfsClient = HdfsClient(os.getenv("HADOOP_NAMENODE_HOST"))

		self._active = False
		self._target_id = None
		self._zk_node_path = None

		self._range = None

		self._trie = None

		scheduler = BackgroundScheduler(timezone="UTC")
		scheduler.add_job(self._attempt_to_join_any, 'interval', minutes=1)
		scheduler.start()

	def start(self):
		self._zk.start()
		datawatch_next_target = DataWatch(client=self._zk, path=ZK_NEXT_TARGET, func=self._on_next_target_changed)
		datawatch_current_target = DataWatch(client=self._zk, path=ZK_CURRENT_TARGET, func=self._on_current_target_changed)

	def stop(self):
		self._zk.stop()


	def top_phrases_for_prefix(self, prefix):
		if (not self._active):
			raise NodeInactiveError("This backend node is not active. Consult zookeeper for the most recent active nodes")
		return self._trie.top_phrases_for_prefix(prefix)

	def _on_next_target_changed(self, data, stat, event=None):
		self._logger.info("_on_next_target_changed Data is %s" % data)
		if (data is None):
			return

		current_target_id = self._zk.get(ZK_CURRENT_TARGET)[0].decode()
		next_target_id = data.decode()
		self._deactivate_if_not_used(current_target_id, next_target_id)
		
		success = self._attempt_to_join_target(next_target_id)

	def _on_current_target_changed(self, data, stat):
		self._logger.info("_on_current_target_changed Data is %s" % data)
		if (data is None):
			return

		current_target_id = data.decode()
		next_target_id = self._zk.get(ZK_NEXT_TARGET)[0].decode()
		self._deactivate_if_not_used(current_target_id, next_target_id)


	def _deactivate_if_not_used(self, current_target_id, next_target_id):
		if (self._active and 
			self._target_id and
			current_target_id != self._target_id and 
			next_target_id != self._target_id):
			self._logger.info(f'Deactivating {self._target_id}, {current_target_id}, {next_target_id}')

			if (self._zk.exists(self._zk_node_path)):
				self._zk.delete(self._zk_node_path)

			self._active = False
			self._target_id = None
			self._trie = None
			self._zk_node_path = None


	def _attempt_to_join_any(self):
		self._logger.debug("Attempting to join any")
		if (self._active):
			return 
		if (self._zk.exists(ZK_CURRENT_TARGET) is not None):
			target_id = self._zk.get(ZK_CURRENT_TARGET)[0].decode()
			if (self._attempt_to_join_target(target_id)):
				return
		if (self._zk.exists(ZK_NEXT_TARGET) is not None):
			target_id = self._zk.get(ZK_NEXT_TARGET)[0].decode()
			if(self._attempt_to_join_target(target_id)):
				return


	def _attempt_to_join_target(self, target_id):
		if (self._active):
			return False

		if (not target_id or self._zk.exists(f'/phrases/distributor/{target_id}') is None):
			return False

		self._logger.info(f'Attempting to join {target_id}')

		partitions = self._zk.get_children(f'/phrases/distributor/{target_id}/partitions')
		for partition in partitions:

			nodes_path = f'/phrases/distributor/{target_id}/partitions/{partition}/nodes/'

			self._zk.sync(nodes_path)
			nodes = self._zk.get_children(nodes_path)
			if (len(nodes) >= NUMBER_NODES_PER_PARTITION):
				self._logger.info(f'Cannot join {nodes_path}, it has enough nodes {nodes}; current number of nodes {len(nodes)} >= {NUMBER_NODES_PER_PARTITION}')
				continue # No more nodes needed here
			
			created_node_path = self._zk.create(nodes_path, value=b'', ephemeral=True, sequence=True)
			self._zk_node_path = created_node_path

			try:
				created_node_name = created_node_path.split('/')[-1]

				self._zk.sync(nodes_path)
				nodes = self._zk.get_children(nodes_path)
				nodes.sort()

				if (nodes and int(created_node_name) > int(nodes[0:NUMBER_NODES_PER_PARTITION][-1])):
					# The node was not able to join the partition
					self._logger.info(f'Cannot join {nodes_path}, it has already filled up {nodes}; created_node_name: {created_node_name}')
					self._zk.delete(created_node_path)
					continue

				if (not self._load_trie_and_activate(target_id, partition)):
					self._logger.error(f'Error while loading and activating trie for {nodes_path}, target_id: {target_id}, partition: {partition}')
					self._zk.delete(created_node_path)
					continue

				# Finishes the initialization
				self._zk.set(created_node_path, socket.gethostname().encode())

				return True
			except:
				self._zk.delete(created_node_path)


		return False

	def _load_trie_and_activate(self, target_id, partition):
		trie_data_hdfs_path = f'/phrases/distributor/{target_id}/partitions/{partition}/trie_data_hdfs_path'
		trie = self._load_trie(self._zk.get(trie_data_hdfs_path)[0].decode())
		if (trie):
			self._trie = trie
			self._active = True
			self._target_id = target_id
			self._logger.info(f'Now ACTIVE and loaded trie for partition {partition} and target_id {target_id}')
			return True
		else:
			return False

	def _load_trie(self, trie_hdfs_path):
		local_path = 'trie.dat'
		self._hdfsClient.download(trie_hdfs_path, local_path)
		with open(local_path, 'rb') as f:
		    return pickle.load(f)
