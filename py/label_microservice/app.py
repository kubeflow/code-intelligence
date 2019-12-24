"""Flask app for the label microservice."""

import flask
import logging
import os

from label_microservice import universal_kind_label_model as universal_model

app = flask.Flask(__name__)

@app.route("/health_check", methods=["GET"])
def health_check():
  """Return a health check."""
  return flask.jsonify({'success':True}), 200, {'ContentType':'application/json'}

@app.route("/predict", methods=["POST"])
def predict():
  """Predict labels given issuse title and text.

  The request payload should contain a json dictionary with two keys "title"
  and "text" containing the title and text for the issue.

  The field model can be used to select the model.

  Returns:
    json response containing a dictionary mapping labels to predicted
    probabilities.
  """
  content = flask.request.json

  model_name = content.get("model", "")
  title = content.get("title", "")
  text = content.get("text", "")

  # TODO(jlewi): How can we initialize the model once for the app and reuse it
  logging.info("Loading the universal model")
  models = {
    "universal": universal_model.UniversalKindLabelModel()
  }

  if not model_name in models:
    logging.error(f"No model named {model_name}")
    response = {
      "error": (f"No model named {model_name}. Allowed values are"
                f"[{','.join(models.keys())}]")
    }
    return flask.jsonify(response), 200, {'ContentType':'application/json'}

  model = models[model_name]
  logging.info(f"Generating predictions for title={title} text={text}")
  predictions = model.predict_issue_labels(title, text)
  logging.info(f"Predictions for title={title} text={text}\n{predictions}")

  logging.info("Hack code")
  return flask.jsonify(response), 200, {'ContentType':'application/json'}

if __name__ == "__main__":
  # make sure things reload
  app.jinja_env.auto_reload = True
  app.config['TEMPLATES_AUTO_RELOAD'] = True
  app.run(debug=True, host='0.0.0.0', port=os.getenv('PORT'))
