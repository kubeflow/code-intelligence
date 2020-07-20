import sys
import yaml

class CRDPruner:
  @staticmethod
  def edit(path):
    with open(path) as hf:
      crd = yaml.load(hf)

    # TODO(https://github.com/kubeflow/code-intelligence/issues/172)
    # https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#controlling-pruning
    crd["spec"]["validation"]["openAPIV3Schema"]["properties"]["spec"]["properties"]["pipelineRunTemplate"] = {
      "type": "object",
      "properties": {
        "json": {
          "x-kubernetes-preserve-unknown-fields": True,
          "type": "object",
          "description": "This should be json parseable as pipelinerun template",
        }}
    }

    with open(path, "w") as hf:
      yaml.dump(crd, hf)

if __name__ == "__main__":
  CRDPruner.edit(sys.argv[1])
