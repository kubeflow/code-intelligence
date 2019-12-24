"""Flask app for the label microservice."""

import flask
import os

app = flask.Flask(__name__)

@app.route("/health_check", methods=["GET"])
def health_check():
  """Return a health check"""
  return flask.jsonify({'success':True}), 200, {'ContentType':'application/json'}

@app.route("/predict", methods=["POST"])
def predict():
  "route for load balancer."
  content = flask.request.json
  response = {
    "in_tile": content["title"],
    "in_text": content["text"],
  }
  return flask.jsonify(response), 200, {'ContentType':'application/json'}

if __name__ == "__main__":
  # make sure things reload
  app.jinja_env.auto_reload = True
  app.config['TEMPLATES_AUTO_RELOAD'] = True
  app.run(debug=True, host='0.0.0.0', port=os.getenv('PORT'))
