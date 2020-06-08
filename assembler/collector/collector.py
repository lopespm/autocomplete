import os
import logging
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer


key_schema_str = """
{
   "namespace": "io.github.lopespm.autocomplete.phrases",
   "name": "key",
   "type": "record",
   "fields" : [
     { "name" : "phrase", "type" : "string" }
   ]
}
"""

value_schema_str = """
{
   "namespace": "io.github.lopespm.autocomplete.phrases",
   "name": "value",
   "type": "record",
   "fields" : [
     { "name" : "phrase", "type" : "string" }
   ]
}
"""

class Collector:

	def __init__(self):
		self._logger = logging.getLogger('gunicorn.error')

		value_schema = avro.loads(value_schema_str)
		key_schema = avro.loads(key_schema_str)

		self._producer = AvroProducer({
			'bootstrap.servers': f'{os.getenv("BROKER_HOST")}:9092',
			'schema.registry.url': f'http://{os.getenv("SCHEMA_REGISTRY_HOST")}:8081',
			'on_delivery': self._delivery_report
			}, default_key_schema=key_schema, default_value_schema=value_schema)

	def collect_phrase(self, phrase):
		phrase = phrase.lower().translate({ord(i): None for i in '|'}) # Remove pipe characther, which is treated as a special character in this system 
		self._producer.produce(topic='phrases', value={"phrase": phrase}, key={"phrase": phrase})
		self._producer.flush()

	def _delivery_report(self, err, msg):
		""" Called once for each message produced to indicate delivery result. Triggered by poll() or flush(). """
		if err is not None:
		    self._logger.error('Message delivery to broker failed: {}'.format(err))
		else:
		    self._logger.info('Message delivered to broker on {} [{}]'.format(msg.topic(), msg.partition()))
