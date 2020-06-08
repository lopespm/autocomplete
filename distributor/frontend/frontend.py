import os
import requests
import random
import logging
import redis
import pickle
from distutils.util import strtobool
from kazoo.client import KazooClient, DataWatch

ZK_CURRENT_TARGET = '/phrases/distributor/current_target'
DISTRIBUTED_CACHE_TOP_PHRASES_KEY = 'top-phrases:'


class BackendNodesNotAvailable(Exception):
	pass

class Frontend:

	def __init__(self):
		self._logger = logging.getLogger('gunicorn.error')
		self._zk = KazooClient(hosts=f'{os.getenv("ZOOKEEPER_HOST")}:2181')
		self._distributed_cache = redis.Redis(host=os.getenv("DISTRIBUTED_CACHE_HOST"), port=6379, db=0)
		self._distributed_cache_enabled = bool(strtobool(os.getenv('DISTRIBUTED_CACHE_ENABLED', 'true')))

	def start(self):
		self._zk.start()

	def stop(self):
		self._zk.stop()		

	# Using Cache Aside Pattern
	def top_phrases_for_prefix(self, prefix):
		top_phrases_from_distributed_cache = self._top_phrases_for_prefix_distributed_cache(prefix)
		if (top_phrases_from_distributed_cache is not None):
			self._logger.debug(f'Got top phrases from distributed cache: {top_phrases_from_distributed_cache}')
			return top_phrases_from_distributed_cache

		backend_hostname = self._random_backend_for_prefix(prefix)

		if (backend_hostname is None):
			raise BackendNodesNotAvailable("No backend nodes available to complete the request")

		self._logger.debug(f'Getting phrases from host {backend_hostname}')
		r = requests.get(f'http://{backend_hostname}:8001/top-phrases', params = {'prefix': prefix})
		self._logger.debug(f'request content: {r.content}; r.json(): {r.json()}')
		top_phrases = r.json()["data"]["top_phrases"]
		self._insert_top_phrases_distributed_cache(prefix, top_phrases)

		return top_phrases


	def _top_phrases_for_prefix_distributed_cache(self, prefix):
		if (not self._distributed_cache_enabled):
			return None

		key = DISTRIBUTED_CACHE_TOP_PHRASES_KEY + prefix
		self._logger.debug(f'Attempting to get top phrases from distributed cache with key {key}')
		if (self._distributed_cache.exists(key)):
			pickled_list = self._distributed_cache.get(key)
			return pickle.loads(pickled_list)
		return None

	def _insert_top_phrases_distributed_cache(self, prefix, top_phrases):
		if (not self._distributed_cache_enabled):
			return

		key = DISTRIBUTED_CACHE_TOP_PHRASES_KEY + prefix
		time_to_expire_s = 30 * 60 # Expire entry after 30 minutes
		self._logger.debug(f'Inserting top phrases tokey {key}, with top phrases {top_phrases}')
		self._distributed_cache.set(key, pickle.dumps(top_phrases), ex=time_to_expire_s)


	def _random_backend_for_prefix(self, prefix):

		if (self._zk.exists(ZK_CURRENT_TARGET) is None):
			return None

		target_id = self._zk.get(ZK_CURRENT_TARGET)[0].decode()
		if (not target_id):
			return None

		partitions = self._zk.get_children(f'/phrases/distributor/{target_id}/partitions')
		for partition in partitions:
			start, end = partition.split('|')
			if ((not start or prefix >= start) and (not end or prefix < end)):
				nodes_path = f'/phrases/distributor/{target_id}/partitions/{partition}/nodes'

				nodes = self._zk.get_children(nodes_path)
				random.shuffle(nodes)

				while nodes:
					node = nodes.pop()
					hostname = self._zk.get(f'{nodes_path}/{node}')[0].decode()
					if (hostname):
						return hostname

				self._logger.warn(f'The partition {partition} does not have any active nodes')
				return None

		return None
