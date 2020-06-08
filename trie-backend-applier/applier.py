import os
import time
import logging
from kazoo.client import KazooClient, DataWatch
from apscheduler.schedulers.blocking import BlockingScheduler

ZK_CURRENT_TARGET = '/phrases/distributor/current_target'
ZK_NEXT_TARGET = '/phrases/distributor/next_target'
NUMBER_NODES_PER_PARTITION = int(os.getenv("NUMBER_NODES_PER_PARTITION"))


class Applier:

	def __init__(self):
		self._zk = KazooClient(hosts=f'{os.getenv("ZOOKEEPER_HOST")}:2181')
		self._logger = logging.getLogger(__name__)
		self._logger.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))
		ch = logging.StreamHandler()
		ch.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))
		self._logger.addHandler(ch)

	def start(self):
		self._logger.debug("Applier started")
		self._zk.start()
		self._attempt_to_apply_next_target()

		scheduler = BlockingScheduler(timezone="UTC")
		scheduler.add_job(self._attempt_to_apply_next_target, 'interval', minutes=1)
		scheduler.start()

	def stop(self):
		self._zk.stop()



	def _attempt_to_apply_next_target(self):
		if (self._is_next_target_ready()):
			self._apply_next_target()


	def _apply_next_target(self):
		self._logger.info("Applying next target")
		self._zk.ensure_path(ZK_CURRENT_TARGET)
		next_target_id = self._zk.get(ZK_NEXT_TARGET)[0]

		tx = self._zk.transaction()
		tx.set_data(ZK_NEXT_TARGET, b'')
		tx.set_data(ZK_CURRENT_TARGET, next_target_id)
		tx.commit()


	def _is_next_target_ready(self):
		if (self._zk.exists(ZK_NEXT_TARGET) is None):
			return False

		next_target_id = self._zk.get(ZK_NEXT_TARGET)[0].decode()
		if (not next_target_id or self._zk.exists(f'/phrases/distributor/{next_target_id}') is None):
			return False

		partitions = self._zk.get_children(f'/phrases/distributor/{next_target_id}/partitions')
		if (not partitions):
			return False

		for partition in partitions:
			nodes_path = f'/phrases/distributor/{next_target_id}/partitions/{partition}/nodes'
			nodes = self._zk.get_children(nodes_path)

			if (len(nodes) < NUMBER_NODES_PER_PARTITION):
				return False

			for node in nodes:
				hostname = self._zk.get(f'{nodes_path}/{node}')[0].decode()
				if (not hostname):
					return False

		return True


if __name__ == '__main__':
	applier = Applier()
	applier.start()
	
	while True:
		time.sleep(5)
