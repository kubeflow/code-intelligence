import logging
from pathlib import Path
import os
import sys

def setup():
  """Do some basic setup."""
  logging.basicConfig(format='%(message)s')
  logging.getLogger().setLevel(logging.INFO)

  home = str(Path.home())

  # Installing the python packages locally doesn't appear to have them automatically
  # added the path so we need to manually add the directory
  local_py_path = os.path.join(home, ".local/lib/python3.6/site-packages")

  for p in [local_py_path, os.path.abspath("../../py")]:
      if p not in sys.path:
        logging.info("Adding %s to python path", p)
        # Insert at front because we want to override any installed packages
        sys.path.insert(0, p)

