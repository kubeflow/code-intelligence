package pkg

import (
	"github.com/aws/aws-sdk-go/private/util"
	"reflect"
	"testing"
)

func Test_FindOwners(t *testing.T) {
	type testCase struct {
		QueryParameters map[string]string
		Expected []string
	}

	testCases := []*testCase {
		{
			QueryParameters:  map[string]string{
				"area": "jupyter",
			},
			Expected: [] string{
				"area/jupyter",
			},
		},
		{
			QueryParameters:  map[string]string{
				"platform": "gcp",
			},
			Expected: [] string{
				"platform/gcp",
			},
		},
		{
			QueryParameters:  map[string]string{
				"platform": "",
			},
			Expected: [] string{},
		},
	}


	s := &KubeflowLabels{
		Labels: map[string]LabelInfo {
			"area/jupyter": LabelInfo{},
			"platform/gcp": LabelInfo{},
		},
	}
	for _, c := range testCases {
		actual := s.matchLabels(c.QueryParameters)

		if !reflect.DeepEqual(actual, c.Expected) {
			t.Errorf("Got %v; Want %v", util.PrettyPrint(actual), util.PrettyPrint(c.Expected))
		}
	}
}