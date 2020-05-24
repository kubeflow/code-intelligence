package pkg

import (
	"os"
	"path"
	"testing"
)

func Test_ParseLabels(t *testing.T) {
	wd , err := os.Getwd()

	if err != nil {
		t.Fatalf("Could not get working directory; %v", err)
	}

	testFile := path.Join(wd, "test_data", "labels-owners.yaml")

	_, err = LoadLabels(testFile)

	if err != nil {
		t.Fatalf("Could not load labels from %v; error: %v", testFile, err)
	}
}