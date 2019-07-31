import logging
import json

def write_items_to_json(output_file, results):
  with open(output_file, "w") as hf:
    for i in results:
      json.dump(i, hf)
      hf.write("\n")
  logging.info("Wrote %s items to %s", len(results), output_file)