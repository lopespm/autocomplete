import falcon
import json
import logging
from collector import Collector


class MainResource(object):
	def __init__(self):
		self._logger = logging.getLogger('gunicorn.error')
		self._collector = Collector()

	def on_post(self, req, resp):
		self._logger.debug(f'Handling request {req.url} with params {req.params}')

		try:
			self._collector.collect_phrase(req.params['phrase'])
			response_body = json.dumps(
				{
					"status": "success",
					"message": "Phrase sent for collection"
				 })
			resp.status = falcon.HTTP_200
			resp.body = response_body
			
		except Exception as e:
			self._logger.error('An error occurred when processing the request', exc_info=e)
			response_body = json.dumps(
				{
					"status": "error",
					"message": "An error occurred when processing the request"
				 })
			resp.status = falcon.HTTP_500
			resp.body = response_body


app = falcon.API()
main_resource = MainResource()
app.add_route('/collect-phrase', main_resource)
