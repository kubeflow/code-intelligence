# Autoupdate go-code

This directory contains the code for continuously updating the model in production to the latest model.

There are two binaries

./main.go - This is the binary for the ModelSync custom controller
./cmd/automl/main.go - This is a binary for a CLI and http server that is used to
  * Determine if a model update is necessary
  * Add labels to AutoML models

