"""Flask app for the label microservice."""

import http
import flask
import logging
import os

from label_microservice import combined_model
from label_microservice import repo_specific_model
from label_microservice import universal_kind_label_model as universal_model

app = flask.Flask(__name__)

# Keep track of all the models that can be used
app.config["models"] = {}

def load_models():
  # TODO(jlewi): How can we initialize the model once for the app and reuse it
  logging.info("Loading the universal model")
  app.config["models"]["universal"] = universal_model.UniversalKindLabelModel()

  for org_and_repo in [("kubeflow", "kubeflow")]:
    org = org_and_repo[0]
    repo = org_and_repo[1]
    logging.info(f"Loading model for repo {org}/{repo}")

    repo_model = repo_specific_model.RepoSpecificLabelModel.from_repo(
      org, repo)

    app.config["models"][f"{org}/{repo}"] = repo_model

    app.config["models"][f"{org}/{repo}_combined"] = combined_model.CombinedLabelModels(
      models=[app.config["models"]["universal"], repo_model])

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

  errors = []

  if not app.config["models"]:
    # TODO(jlewi): This is a hack because when I loaded the models before
    # calling app.run I ended up hitting what looked like threading issues
    # because the requested TF ops weren't found in the graph. But Loading
    # the models inside the first request appears to work.
    logging.info("Loading models")
    load_models()


  if not model_name:
      known_models = ",".join(app.config["models"].keys())
      errors.append("Request is missing field model containing the name of the "
                    "model to use to generate predictions. Allowed values: "
                    f"{known_models}")

  if model_name and not model_name in app.config["models"]:
    errors.append(f"No model named {model_name}")

  if errors:
    error_message = "\n".join(errors)
    logging.error(f"Request had errors: {error_message}")

    response = {
      "errors": errors
    }
    return (flask.jsonify(response), http.HTTPStatus.BAD_REQUEST.value,
            {'ContentType':'application/json'})

  model = app.config["models"][model_name]
  logging.info(f"Generating predictions for title={title} text={text}")
  predictions = model.predict_issue_labels(title, text)
  logging.info(f"Predictions for title={title} text={text}\n{predictions}")

  return (flask.jsonify(predictions), http.HTTPStatus.OK,
          {'ContentType':'application/json'})

if __name__ == "__main__":
  logging.basicConfig(level=logging.INFO,
                      format=('%(levelname)s|%(asctime)s'
                              '|%(message)s|%(pathname)s|%(lineno)d|'),
                      datefmt='%Y-%m-%dT%H:%M:%S',
                      )
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
