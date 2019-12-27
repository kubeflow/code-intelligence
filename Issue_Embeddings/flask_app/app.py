import hashlib
import os
import logging
from flask import (abort, Flask, session, render_template,
                   session, redirect, url_for, request,
                   flash, jsonify)
from flask_session import Session
from urllib import request as request_url
from pathlib import Path
from inference import InferenceWrapper, pass_through

app = Flask(__name__)

# Configure session to use filesystem. Hamel: BOILERPLATE.
app.config["SESSION_PERMANENT"] = False
Session(app)

LOG = logging.getLogger(__name__)

def init_language_model():
    """
    Downloads pre-trained language model and instantiates inference mechanism.
    """
    model_url = 'https://storage.googleapis.com/issue_label_bot/model/lang_model/models_22zkdqlr/trained_model_22zkdqlr.pkl'
    path = Path('./model_files')
    full_path = path/'model.pkl'

    if not full_path.exists():
        print('Loading model.')
        path.mkdir(exist_ok=True)
        request_url.urlretrieve(model_url, path/'model.pkl')

    app.inference_wrapper = InferenceWrapper(model_path=path, model_file_name='model.pkl')
    LOG.warning('Finished loading model.')


@app.route("/healthz", methods=["GET"])
def healthz():
    "route for health check."
    return jsonify({'success':True}), 200, {'ContentType':'application/json'}


@app.route("/", methods=["GET"])
def index():
    "Landing page"
    return render_template("index.html")

# smee by default sends things to /event_handler route
@app.route("/text", methods=["POST"])
def text():
    """
    Route that allows user to send json with raw text of title and body.  This
    route expects a payload to be sent that contains:

    {'title': "some text ...",
    'body': "some text ....}
    """

    # pre-process data
    title = request.json['title']
    body = request.json['body']

    logging.debug(f"Recieved title={title} body={body}")
    data = app.inference_wrapper.process_dict({'title':title, 'body':body})
    logging.debug(f'prediction requested for {str(data)}')

    # make prediction: you can only return strings with api
    # decode with np.frombuffer(request.content, dtype='<f4')
    embeddings_str = app.inference_wrapper.get_pooled_features(data['text']).detach().numpy().tostring()

    # For debugging print out hash of the content embeddings. This is to
    # see if they are changing
    m = hashlib.md5()
    m.update(embeddings_str)
    logging.debug(f"hash of embeddings {m.hexdigest()}")
    return embeddings_str

@app.route("/all_issues/<string:owner>/<string:repo>", methods=["POST"])
def fetch_issues(owner, repo):
    """
    Retrieve the embeddings for all the issues of a repo.
    """
    #TODO: finish this
    #TODO(jlewi): I'm not sure we want to finish this method. It might be
    #better if the embedding service wasn't aware of GitHub; i.e. the input
    #was always title and text. Any interactions with GitHub should then
    #happen in microservices in front of this one.
    return NotImplementedError()

    installed = app_installation_exists(owner=owner, repo=repo)
    if not installed:
        abort(400, description="The app is not installed on this repository.")

    if not is_public(owner, repo):
        abort(400, description="This app only works on public repositories.")

def is_public(owner, repo):
    "Verify repo is public."
    try:
        return requests.head(f'https://github.com/{owner}/{repo}').status_code == 200
    except:
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format=('%(levelname)s|%(asctime)s'
                                '|%(message)s|%(pathname)s|%(lineno)d|'),
                        datefmt='%Y-%m-%dT%H:%M:%S',
                        )
    init_language_model()

    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower()

    # Need to convert it to boolean
    if FLASK_DEBUG in ["true", "t"]:
        FLASK_DEBUG = True
    else:
        FLASK_DEBUG = False

    logging.info(f"FLASK_DEBUG={FLASK_DEBUG}")

    if FLASK_DEBUG:
        raise ValueError(f"Flask debug mode currently doesn't work with the "
                         f"embedding model. See "
                         f"https://github.com/kubeflow/code-intelligence/pull/77#issuecomment-569105812")

    app.run(debug=FLASK_DEBUG, host='0.0.0.0',
            port=os.getenv('PORT'), threaded=False)
