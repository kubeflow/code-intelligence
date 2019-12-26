"""Flask app for the label microservice."""

import http
import flask
import logging
import os

from label_microservice import issue_label_predictor
from label_microservice import worker

app = flask.Flask(__name__)

# Keep track of all the models that can be used
app.config["predictor"] = None

# TODO(jlewi): get_predictor should only be called in the handler for a
# prediction request; trying to preinitialize the predictor before run is
# called ended up hitting what looked like threading issues
# because the requested TF ops weren't found in the graph. But Loading
# the models inside the first request appears to work.
# I need to try to find some way to preload all the models before the first
# request is recieved
def get_predictor():
  if not app.config["predictor"]:
    logging.info("Creating label predictor")
    app.config["predictor"] = issue_label_predictor.IssueLabelPredictor()

  return app.config["predictor"]

@app.route("/health_check", methods=["GET"])
def health_check():
  """Return a health check."""
  return flask.jsonify({'success':True}), 200, {'ContentType':'application/json'}

@app.route("/predict", methods=["POST"])
def predict():
  """Predict labels given issuse title and text.

  The request payload should look like one of the following.

  The field model can be used to select the model.

  Returns:
    json response containing a dictionary mapping labels to predicted
    probabilities.
  """
  print("DO NOT SUBMIT this is a test for the file sync and reloader")
  content = flask.request.json

  predictor = get_predictor()

  try:
    predictions = predictor.predict(content)
  except ValueError as e:
    response = {
      "errors": [f"{e}"]
    }
    return (flask.jsonify(response), http.HTTPStatus.BAD_REQUEST.value,
            {'ContentType':'application/json'})

  return (flask.jsonify(predictions), http.HTTPStatus.OK,
          {'ContentType':'application/json'})

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                      format=('%(levelname)s|%(asctime)s'
                              '|%(message)s|%(pathname)s|%(lineno)d|'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )

  logging.info("Starting pubsub worker")
  # TODO(jlewi): What is the right way to start the pubsub worker so that
  # when running under skaffold we can use the flask reloader to trigger
  # a reload and restart when the code changes
  issue_worker = worker.Worker.subscribe_from_env()

  # make sure things reload
  app.jinja_env.auto_reload = True
  app.config['TEMPLATES_AUTO_RELOAD'] = True
  logging.info("Starting flask app")

  # TODO(jlewi): If we don't set threaded=False then when we do inference
  # we get errors about certain tensors not being found. This is probably
  # due to tf.graph (not multi-thread safe?) and flask interact.
  # It doesn't look like the original flask app is setting threaded=False
  # https://github.com/machine-learning-apps/Issue-Label-Bot/blob/master/flask_app/app.py#L415
  # Need to investigate to figure out what's different
  app.run(threaded=False, debug=True, host='0.0.0.0', port=os.getenv('PORT'))
