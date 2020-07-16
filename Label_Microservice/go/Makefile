
# Image URL to use all building/pushing image targets
IMG ?= controller:latest
# Produce CRDs that work back to Kubernetes 1.11 (no version conversion)

CRD_OPTIONS ?= "crd:trivialVersions=true"

# TODO(jlewi): Need to sort out root vs project level Makefiles
CONTEXT=label-bot-dev

# Get the currently used golang install path (in GOPATH/bin, unless GOBIN is set)
ifeq (,$(shell go env GOBIN))
GOBIN=$(shell go env GOPATH)/bin
else
GOBIN=$(shell go env GOBIN)
endif

all: manager

# Run tests
test: generate fmt vet manifests
	go test ./... -coverprofile cover.out

# Build manager binary
manager: generate fmt vet
	go build -o bin/manager main.go

# Run against the configured Kubernetes cluster in ~/.kube/config
run: generate fmt vet manifests
	go run ./main.go start

# Install CRDs into a cluster
install: manifests
	kustomize build config/crd | kubectl apply -f -

# Uninstall CRDs from a cluster
uninstall: manifests
	kustomize build config/crd | kubectl delete -f -

# Deploy controller in the configured Kubernetes cluster in ~/.kube/config
deploy: manifests
	cd config/manager && kustomize edit set image controller=${IMG}
	kustomize build config/default | kubectl apply -f -

# Generate manifests e.g. CRD, RBAC etc.
manifests: controller-gen
	$(CONTROLLER_GEN) $(CRD_OPTIONS) rbac:roleName=manager-role webhook paths="./..." output:crd:artifacts:config=config/crd/bases
	# We need to do some custom pruning of the Kubeflow CRD definition.
	# In particular we need to change the type of pipelineRunTemplate to arbitrary json and not specify the schema for two reasons
	# 1. Specifying that schema leads to a CRD that exceeds APIServer limits 
	#    * We can potentially work around this by using CRD_OPTIONS maxDescLen=0 to prune just the descriptions
	# 2. The generated openapi spec for pipelineruntemplate rejects valid pipelineruntemplates
	#    the problem appears to be that tekton does some custom deserialization of params in order to treat them
	#    as strings or arrays
	python ./hack/prune_crd.py ./config/crd/bases/automl.cloudai.kubeflow.org_modelsyncs.yaml


# Run go fmt against code
fmt:
	go fmt ./...

# Run go vet against code
vet:
	go vet ./...

# Generate code
generate: controller-gen
	$(CONTROLLER_GEN) object:headerFile="hack/boilerplate.go.txt" paths="./..."

build-image:
	skaffold build --kube-context=${CONTEXT} -v info --file-output=controller.image.json

set-image:
	cd config/manager && kustomize edit set image controller=$(shell yq r controller.image.json builds[0].tag )

# TODO(jlewi): Using skaffold is preferred
# Build the docker image
docker-build: test
	docker build . -t ${IMG}

# Push the docker image
docker-push:
	docker push ${IMG}

# find or download controller-gen
# download controller-gen if necessary
controller-gen:
ifeq (, $(shell which controller-gen))
	@{ \
	set -e ;\
	CONTROLLER_GEN_TMP_DIR=$$(mktemp -d) ;\
	cd $$CONTROLLER_GEN_TMP_DIR ;\
	go mod init tmp ;\
	go get sigs.k8s.io/controller-tools/cmd/controller-gen@v0.2.5 ;\
	rm -rf $$CONTROLLER_GEN_TMP_DIR ;\
	}
CONTROLLER_GEN=$(GOBIN)/controller-gen
else
CONTROLLER_GEN=$(shell which controller-gen)
endif
