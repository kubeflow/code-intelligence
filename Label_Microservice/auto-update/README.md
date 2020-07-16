# Auto update kustomize package

This directory contains a kustomize package to create resources needed to continuosly update
the label bot model.

## ModelSync Custom Resource

The model sync custom resource is a custom controller which fires off a tekton pipeline
whenever a lambda indicates a sync is needed.


### Running the controller locally

1. First install the up to date CRD definitions in your cluster

```
make install
```

1. Disable webhooks since the controller is running locally

```
export ENABLE_WEBHOOKS=false

```

1. Start the control

```
./controller start
```

1. Assuming your are running the NeedsSync service in the cluster you need to setup port forwarding

```
kubectl port-forward service/${SERVICE} 8080:80
```

1. Edit the sample `config/samples/modelsync_local.yaml` as needed

1. Apply it

```
kubectl apply -f config/samples/modelsync_local.yaml
```