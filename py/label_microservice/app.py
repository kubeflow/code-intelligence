"""Flask app for the label microservice."""

import flask
import os

app = flask.Flask(__name__)

@app.route("/health_check", methods=["GET"])
def health_check():
    "route for load balancer."
    return flask.jsonify({'success':True}), 200, {'ContentType':'application/json'}

if __name__ == "__main__":
  # make sure things reload
  app.jinja_env.auto_reload = True
  app.config['TEMPLATES_AUTO_RELOAD'] = True
  app.run(debug=True, host='0.0.0.0', port=os.getenv('PORT'))
