package pkg

import (
	"github.com/ghodss/yaml"
	gogetter "github.com/hashicorp/go-getter"
	"github.com/pkg/errors"
	"io/ioutil"
)

// KubeflowLabels is a struct representing information about Kubeflow labels.
// We deserialize https://github.com/kubeflow/community/blob/master/labels-owners.yaml
// into this file.
type KubeflowLabels struct {
	Labels map[string]LabelInfo `json:"labels,omitempty"`
}

// LabelInfo provides information about a specific label.
type LabelInfo struct{
	Owners []string `json:"owners,omitempty"`
}

// LoadLabels loads the labels from the given URI. The URI can be any URI understood by hashi-corps go-getter.
func LoadLabels(labelMapUri string) (*KubeflowLabels, error) {
	localCopy, err := ioutil.TempFile("", "chatBotLabelMap.yaml")

	if err != nil {
		return nil, errors.WithStack(err)
	}

	if err := gogetter.GetFile(localCopy.Name(), labelMapUri); err != nil {
		return nil, errors.WithStack(errors.Wrapf(err, "Could not get file  %v", labelMapUri))
	}

	contents, err := ioutil.ReadFile(localCopy.Name())

	if err != nil {
		return nil, errors.WithStack(errors.Wrapf(err, "Could not read file: %v; which is a copy of %v", localCopy, labelMapUri))
	}

	labels := &KubeflowLabels{}
	if err := yaml.Unmarshal(contents,labels); err != nil {
		return nil, errors.WithStack(errors.Wrapf(err, "Error trying to deserialize %v (which is a copy of %v) to KubeflowLabels; this likely means the YAML file isn't formatted correctly", localCopy, labelMapUri))
	}

	return labels, nil
}

// GetLabelOwners returns the owners of the given label.
// Returns an empty array if the label is unknown.
func (l *KubeflowLabels) GetLabelOwners(area string)[]string {
	i, ok := l.Labels[area]

	if !ok {
		return []string{}
	}

	return i.Owners
}