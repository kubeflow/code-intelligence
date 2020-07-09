package kpt

import (
	"bytes"
	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
	"io/ioutil"
	"sigs.k8s.io/kustomize/kyaml/kio"
	kyaml "sigs.k8s.io/kustomize/kyaml/yaml"
)

func readYaml(path string) ([]*kyaml.RNode, error) {
	data, err := ioutil.ReadFile(path)
	if err != nil {
		return nil, errors.Wrapf(err, "Error reading path %v", path)
	}

	input := bytes.NewReader(data)
	reader := kio.ByteReader{
		Reader: input,
		// We need to disable adding reader annotations because
		// we want to run some checks about whether annotations are set and
		// adding those annotations interferes with that.
		OmitReaderAnnotations: true,
	}

	nodes, err := reader.Read()

	if err != nil {
		return nil, errors.Wrapf(err, "Error unmarshaling %v", path)
	}

	return nodes, nil
}

// GetSetter gets the value of the specified setter in a KptFile.
func GetKptSetter(filePath string, setterPath []string) (string, error) {
	rNodes, err := readYaml(filePath)

	if err != nil {
		return "", errors.WithStack(errors.Wrapf(err, "Error reading %v",  filePath))
	}

	if len(rNodes) != 1 {
		log.Fatalf("Expected 1 node but got many.")
		return "", errors.WithStack(errors.Wrapf(err, "Expected 1 node but got %v.",  len(rNodes)))
	}

	n := rNodes[0]

	f, err  := n.Pipe(kyaml.Lookup("openAPI", "definitions", "io.k8s.cli.setters.automl-model", "x-k8s-cli", "setter", "value"))

	if err != nil {
		return "", errors.WithStack(errors.Wrapf(err, "Couldn't lookup setter %v in file %v;", setterPath, filePath))
	}
	currentModel := f.YNode().Value


	return currentModel, nil
}
