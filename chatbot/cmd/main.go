package main

import (
	"flag"
	"github.com/kubeflow/code-intelligence/chatbot/cmd/options"
	"github.com/kubeflow/code-intelligence/chatbot/pkg"
	"github.com/onrik/logrus/filename"
	log "github.com/sirupsen/logrus"
)

func init() {
	// Add filename as one of the fields of the structured log message
	filenameHook := filename.NewHook()
	filenameHook.Field = "filename"
	log.AddHook(filenameHook)
}

// Run the application.
func Run(opt *options.ServerOption) error {
	log.Info("Creating server")
	server, err := pkg.NewKubeflowInfoServer(opt.AreaConfigPath)
	if err != nil {
		return err
	}


	server.RegisterEndpoints()

	log.Infof("Starting http server.")
	return server.StartHttp(opt.Port)
}

func main() {
	s := options.NewServerOption()
	s.AddFlags(flag.CommandLine)

	flag.Parse()

	if s.AreaConfigPath == "" {
		log.Fatalf("--area-config-path must be specified. This should be the path to a YAML file defining the areas and their associated owners")
	}
	if s.JsonLogFormat {
		// Output logs in a json format so that it can be parsed by services like Stackdriver
		log.SetFormatter(&log.JSONFormatter{})
	}
	if err := Run(s); err != nil {
		log.Fatalf("%v\n", err)
	}
}