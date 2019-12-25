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
models = {}

def load_models():
  global models

  # TODO(jlewi): How can we initialize the model once for the app and reuse it
  logging.info("Loading the universal model")
  models["universal"] = universal_model.UniversalKindLabelModel()

  # TODO(jlewi): The code below is commented out to see if loading the
  # other models is causing problems with the tensors not being found
  # when using the universal kind label model.
  #for org_and_repo in [("kubeflow", "kubeflow")]:
    #org = org_and_repo[0]
    #repo = org_and_repo[1]
    #logging.info(f"Loading model for repo {org}/{repo}")

    #repo_model = repo_specific_model.RepoSpecificLabelModel.from_repo(
      #org, repo)

    #models[f"{org}/{repo}"] = repo_model

    #models[f"{org}/{repo}_combined"] = combined_model.CombinedLabelModels(
      #models=[models["universal"], repo_model])

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
  global models
  content = flask.request.json

  model_name = content.get("model", "")
  title = content.get("title", "")
  text = content.get("text", "")

  errors = []

  if not model_name:
    errors.append("Request is missing field model containing the name of the "
                  "model to use to generate predictions.")

  if model_name and not model_name in models:
    errors.append(f"No model named {model_name}")

  if errors:
    error_message = "\n".join(errors)
    logging.error(f"Request had errors: {error_message}")

    response = {
      "errors": errors
    }
    return (flask.jsonify(response), http.HTTPStatus.BAD_REQUEST.value,
            {'ContentType':'application/json'})

  model = models[model_name]
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
  load_models()
  app.jinja_env.auto_reload = True
  app.config['TEMPLATES_AUTO_RELOAD'] = True
  logging.info("Starting flask app")
  app.run(debug=True, host='0.0.0.0', port=os.getenv('PORT'))
