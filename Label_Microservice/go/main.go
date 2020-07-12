/*


Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package main

import (
	"os"

	"github.com/spf13/cobra"

	"k8s.io/apimachinery/pkg/runtime"
	clientgoscheme "k8s.io/client-go/kubernetes/scheme"
	_ "k8s.io/client-go/plugin/pkg/client/auth/gcp"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/log/zap"

	automlv1alpha1 "github.com/kubeflow/code-intelligence/Label_Microservice/api/v1alpha1"
	"github.com/kubeflow/code-intelligence/Label_Microservice/controllers"
	tk "github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1"
	// +kubebuilder:scaffold:imports
)

var (
	scheme   = runtime.NewScheme()
	setupLog = ctrl.Log.WithName("setup")

	rootCmd = &cobra.Command{
		Short: "An automl model controller",
		Long:  `A controller to synchronize your automl model with your configs`,
	}

	startCmd = &cobra.Command{
		Use:   "start",
		Short: "Start the kubernetes controller.",
		Long:  `starts the controller`,
		Run: func(cmd *cobra.Command, args []string) {
			mgr, err := ctrl.NewManager(ctrl.GetConfigOrDie(), ctrl.Options{
				Scheme:             scheme,
				MetricsBindAddress: metricsAddr,
				Port:               9443,
				LeaderElection:     enableLeaderElection,
				LeaderElectionID:   "b3bc6e44.cloudai.kubeflow.org",
			})
			if err != nil {
				setupLog.Error(err, "unable to start manager")
				os.Exit(1)
			}

			if err = (&controllers.ModelSyncReconciler{
				Client: mgr.GetClient(),
				Log:    ctrl.Log.WithName("controllers").WithName("ModelSync"),
				Scheme: mgr.GetScheme(),
			}).SetupWithManager(mgr); err != nil {
				setupLog.Error(err, "unable to create controller", "controller", "ModelSync")
				os.Exit(1)
			}

			// +kubebuilder:scaffold:builder

			if os.Getenv("ENABLE_WEBHOOKS") != "false" {
				if err = (&automlv1alpha1.ModelSync{}).SetupWebhookWithManager(mgr); err != nil {
					setupLog.Error(err, "unable to create webhook", "webhook", "Captain")
					os.Exit(1)
				}
			}

			setupLog.Info("starting manager")
			if err := mgr.Start(ctrl.SetupSignalHandler()); err != nil {
				setupLog.Error(err, "problem running manager")
				os.Exit(1)
			}
		},
	}
)

var metricsAddr string
var enableLeaderElection bool
var fileName string

func init() {
	_ = clientgoscheme.AddToScheme(scheme)

	_ = automlv1alpha1.AddToScheme(scheme)
	// Need to add Tekton types to the scheme
	_ = tk.AddToScheme(scheme)
	// +kubebuilder:scaffold:scheme

	rootCmd.AddCommand(startCmd)
	startCmd.Flags().StringVarP(&metricsAddr, "metrics-addr", "", ":8080", "The address the metric endpoint binds to.")
	startCmd.Flags().BoolVarP(&enableLeaderElection, "enable-leader-election", "", false, "Enable leader election for controller manager. "+
		"Enabling this will ensure there is only one active controller manager.")
}

func main() {
	// TODO(jlewi): logR is doing structured logging how do we configure it to emit logs as json?
	ctrl.SetLogger(zap.New(zap.UseDevMode(true)))

	rootCmd.Execute()
}