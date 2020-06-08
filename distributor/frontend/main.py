import falcon
import json
import logging
from frontend import Frontend, BackendNodesNotAvailable


class MainResource(object):
	def __init__(self):
		self._logger = logging.getLogger('gunicorn.error')
		self._frontend = Frontend()
		self._frontend.start()

	def on_get(self, req, resp):
		self._logger.debug(f'Handling {req.method} request {req.url} with params {req.params}')
		try:
			top_phrases = self._frontend.top_phrases_for_prefix(req.params['prefix'])
			response_body = json.dumps(
				{
					"status": "success",
					"data": {
						"top_phrases": top_phrases 
					}
				 })
			resp.status = falcon.HTTP_200
			resp.body = response_body
			
		except BackendNodesNotAvailable as err:
			response_body = json.dumps(
				{
					"status": "error",
					"message": "No backend nodes available to complete the request"
				 })
			resp.status = falcon.HTTP_500
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
app.add_route('/top-phrases', main_resource)

