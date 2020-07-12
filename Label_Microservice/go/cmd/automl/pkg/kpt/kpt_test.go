package kpt

import (
	"log"
	"os"
	"path"
	"testing"
)

func TestGetSetter (t *testing.T){
	type testCase struct {
		filePath string
		setterPath []string
		expected string
	}

	wd, err := os.Getwd()

	if err != nil {
		log.Fatalf("Could not get working directiory; error %v", err)
	}

	cases := []testCase {
		{
			filePath: path.Join(wd, "testdata", "Kptfile"),
			setterPath: []string {
				"openAPI", "definitions", "io.k8s.cli.setters.automl-model", "x-k8s-cli", "setter", "automl-model",
			},
			expected: "projects/976279526634/locations/us-central1/models/TCN654213816573231104",
		},
	}

	for _, c := range cases {
		m, err := GetKptSetter(c.filePath, c.setterPath)
		if err != nil {
			t.Errorf("Could not get setter: %v", err)
			continue
		}

		if m != c.expected {
			t.Errorf("Want %v; Got %v", c.expected, m)
		}
	}
}
