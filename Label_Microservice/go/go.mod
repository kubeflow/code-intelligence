module github.com/kubeflow/code-intelligence/Label_Microservice

go 1.13

require (
	cloud.google.com/go v0.60.0
	github.com/go-logr/logr v0.1.0
	github.com/go-yaml/yaml v2.1.0+incompatible // indirect
	github.com/golang/lint v0.0.0-20180702182130-06c8688daad7 // indirect
	github.com/golang/protobuf v1.4.2
	github.com/gotestyourself/gotestyourself v2.2.0+incompatible // indirect
	github.com/klauspost/cpuid v1.2.2 // indirect
	github.com/knative/build v0.1.2 // indirect
	github.com/mattbaird/jsonpatch v0.0.0-20171005235357-81af80346b1a // indirect
	github.com/onrik/logrus v0.6.0
	github.com/onsi/ginkgo v1.11.0
	github.com/onsi/gomega v1.8.1
	github.com/robfig/cron v1.2.0
	github.com/shurcooL/go v0.0.0-20180423040247-9e1955d9fb6e // indirect
	github.com/sirupsen/logrus v1.4.2
	github.com/spf13/cobra v0.0.6
	github.com/tektoncd/pipeline v0.11.0
	// github.com/tektoncd/pipeline v0.14.0
	//github.com/tektoncd/pipeline v0.0.0
	github.com/tidwall/gjson v1.6.0 // indirect
	google.golang.org/api v0.28.0
	google.golang.org/genproto v0.0.0-20200707001353-8e8330bf89df
	gopkg.in/yaml.v2 v2.3.0
	k8s.io/api v0.17.6
	k8s.io/apimachinery v0.17.6
	k8s.io/client-go v11.0.1-0.20190805182717-6502b5e7b1b5+incompatible
	k8s.io/kubernetes v1.14.7
	knative.dev/pkg v0.0.0-20200630170034-2c1a029eb97f
	sigs.k8s.io/controller-runtime v0.5.0
	sigs.k8s.io/testing_frameworks v0.1.1 // indirect
)

// Pin k8s deps to 1.17.6
replace (
	// Work around for missing json tags that breaks code gen
	github.com/tektoncd/pipeline => /home/jlewi/git_tekton
	k8s.io/api => k8s.io/api v0.17.6
	k8s.io/apiextensions-apiserver => k8s.io/apiextensions-apiserver v0.17.6
	k8s.io/apimachinery => k8s.io/apimachinery v0.17.6
	k8s.io/apiserver => k8s.io/apiserver v0.17.6
	k8s.io/client-go => k8s.io/client-go v0.17.6
	k8s.io/code-generator => k8s.io/code-generator v0.17.6
	k8s.io/kube-openapi => k8s.io/kube-openapi v0.0.0-20200410145947-bcb3869e6f29
)
