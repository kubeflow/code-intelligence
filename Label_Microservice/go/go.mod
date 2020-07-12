module github.com/kubeflow/code-intelligence/Label_Microservice

go 1.13

require (
	cloud.google.com/go v0.60.0
	github.com/go-logr/logr v0.1.0
	github.com/go-yaml/yaml v2.1.0+incompatible
	github.com/golang/protobuf v1.4.2
	github.com/gorilla/mux v1.7.3
	github.com/onrik/logrus v0.6.0
	github.com/onsi/ginkgo v1.11.0
	github.com/onsi/gomega v1.8.1
	github.com/pkg/errors v0.9.1
	github.com/sirupsen/logrus v1.4.2
	github.com/spf13/cobra v1.0.0
	github.com/tektoncd/pipeline v0.11.0
	// github.com/tektoncd/pipeline v0.14.0
	//github.com/tektoncd/pipeline v0.0.0
	github.com/tidwall/gjson v1.6.0 // indirect
	google.golang.org/api v0.28.0
	google.golang.org/genproto v0.0.0-20200707001353-8e8330bf89df
	google.golang.org/protobuf v1.25.0
	k8s.io/api v0.17.6
	k8s.io/apimachinery v0.17.6
	k8s.io/client-go v11.0.1-0.20190805182717-6502b5e7b1b5+incompatible
	knative.dev/pkg v0.0.0-20200630170034-2c1a029eb97f
	sigs.k8s.io/controller-runtime v0.5.0
	sigs.k8s.io/kustomize/kyaml v0.4.0
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
