FROM python:3.7.4

COPY / .
RUN pip install -r Issue_Triage/requirements.txt
ENV PYTHONPATH "${PYTHONPATH}:/py"

ENTRYPOINT [ "python", "py/issue_triage/triage.py" ]