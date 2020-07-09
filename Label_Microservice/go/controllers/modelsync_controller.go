/*

ModelSync is closely modeled on the CronJob example
https://github.com/kubernetes-sigs/kubebuilder/blob/master/docs/book/src/cronjob-tutorial/testdata/project/controllers/cronjob_controller.go


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

package controllers

import (
	"context"
	ref "k8s.io/client-go/tools/reference"
	"sort"
	"time"

	"github.com/go-logr/logr"
	automlv1alpha1 "github.com/kubeflow/code-intelligence/Label_Microservice/api/v1alpha1"
	tk "github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"knative.dev/pkg/apis"
	ctrl "sigs.k8s.io/controller-runtime"
	"sigs.k8s.io/controller-runtime/pkg/client"
)

// ModelSyncReconciler reconciles a ModelSync object
type ModelSyncReconciler struct {
	client.Client
	Log    logr.Logger
	Scheme *runtime.Scheme
}

type RunState string

const (
	RunIsFailed    RunState = "Failed"
	RunIsSucceeded RunState = "Succeded"
	RunIsRunning   RunState = "Running"
)

var (
	runOwnerKey = ".metadata.controller"
)

// +kubebuilder:rbac:groups=automl.cloudai.kubeflow.org,resources=modelsyncs,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=automl.cloudai.kubeflow.org,resources=modelsyncs/status,verbs=get;update;patch

// Controller will need rbac permissions to get, create pipelineruns
// +kubebuilder:rbac:groups=tekton.dev,resources=pipelinerun,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=tekton.dev,resources=pipelinerun/status,verbs=get

func (r *ModelSyncReconciler) Reconcile(req ctrl.Request) (ctrl.Result, error) {
	ctx := context.Background()
	log := r.Log.WithValues("modelsync", req.NamespacedName)

	// Load the model syncer
	var modelSync automlv1alpha1.ModelSync
	if err := r.Get(ctx, req.NamespacedName, &modelSync); err != nil {
		log.Error(err, "unable to fetch ModelSync")
		// we'll ignore not-found errors, since they can't be fixed by an immediate
		// requeue (we'll need to wait for a new notification), and we can get them
		// on deleted requests.
		return ctrl.Result{}, client.IgnoreNotFound(err)
	}

	// List all the pipelineruns associated with this ModelSync
	var childRuns tk.PipelineRunList

	if err := r.List(ctx, &childRuns, client.InNamespace(req.Namespace), client.MatchingFields{runOwnerKey: req.Name}); err != nil {
		log.Error(err, "unable to list child PipelineRuns")
		return ctrl.Result{}, err
	}

	// find the active list of pipelineRuns
	var activeRuns []*tk.PipelineRun
	var successfulRuns []*tk.PipelineRun
	var failedRuns []*tk.PipelineRun

	/*  We consider a run "finished" if it has a "succeeded" or "failed" condition marked as true.
	 */
	isRunFinished := func(run *tk.PipelineRun) RunState {
		for _, c := range run.Status.Conditions {
			// Tekton pipelineruns appear to use condition Succeeded with status False and reason Failed in case of failure
			if c.Type == apis.ConditionSucceeded && ((&c).IsTrue() || (&c).IsFalse()) {
				if (&c).IsTrue() {
					return RunIsSucceeded
				} else {
					return RunIsFailed
				}
			}
		}

		return RunIsRunning
	}

	for i, run := range childRuns.Items {
		runState := isRunFinished(&run)
		switch runState {
		case RunIsRunning: // ongoing
			activeRuns = append(activeRuns, &childRuns.Items[i])
		case RunIsFailed:
			failedRuns = append(failedRuns, &childRuns.Items[i])
		case RunIsSucceeded:
			successfulRuns = append(successfulRuns, &childRuns.Items[i])
		}
	}

	modelSync.Status.Active = nil
	for _, activeJob := range activeRuns {
		runRef, err := ref.GetReference(r.Scheme, activeJob)
		if err != nil {
			log.Error(err, "unable to make reference to active run", "job", activeJob)
			continue
		}
		modelSync.Status.Active = append(modelSync.Status.Active, *runRef)
	}

	log.V(1).Info("job count", "active jobs", len(activeRuns), "successful jobs", len(successfulRuns), "failed jobs", len(failedRuns))

	if err := r.Status().Update(ctx, &modelSync); err != nil {
		log.Error(err, "unable to update ModelSync status")
		return ctrl.Result{}, err
	}

	/*
		Once we've updated our status, we can move on to ensuring that the status of
		the world matches what we want in our spec.
		### 3: Clean up old jobs according to the history limit
		First, we'll try to clean up old jobs, so that we don't leave too many lying
		around.
	*/

	// NB: deleting these is "best effort" -- if we fail on a particular one,
	// we won't requeue just to finish the deleting.
	if modelSync.Spec.FailedPipelineRunsHistoryLimit != nil {
		sort.Slice(failedRuns, func(i, j int) bool {
			if failedRuns[i].Status.StartTime == nil {
				return failedRuns[j].Status.StartTime != nil
			}
			return failedRuns[i].Status.StartTime.Before(failedRuns[j].Status.StartTime)
		})
		for i, job := range failedRuns {
			if int32(i) >= int32(len(failedRuns))-*modelSync.Spec.FailedPipelineRunsHistoryLimit {
				break
			}
			if err := r.Delete(ctx, job, client.PropagationPolicy(metav1.DeletePropagationBackground)); client.IgnoreNotFound(err) != nil {
				log.Error(err, "unable to delete old failed job", "job", job)
			} else {
				log.V(0).Info("deleted old failed job", "job", job)
			}
		}
	}

	if modelSync.Spec.SuccessfulPipelineRunsHistoryLimit != nil {
		sort.Slice(successfulRuns, func(i, j int) bool {
			if successfulRuns[i].Status.StartTime == nil {
				return successfulRuns[j].Status.StartTime != nil
			}
			return successfulRuns[i].Status.StartTime.Before(successfulRuns[j].Status.StartTime)
		})
		for i, job := range successfulRuns {
			if int32(i) >= int32(len(successfulRuns))-*modelSync.Spec.SuccessfulPipelineRunsHistoryLimit {
				break
			}
			if err := r.Delete(ctx, job, client.PropagationPolicy(metav1.DeletePropagationBackground)); (err) != nil {
				log.Error(err, "unable to delete old successful job", "job", job)
			} else {
				log.V(0).Info("deleted old successful job", "job", job)
			}
		}
	}

	constructRunForModelSync := func(modelSync *automlv1alpha1.ModelSync) (*tk.PipelineRun, error) {

		run := &tk.PipelineRun{}
		run.Spec = *modelSync.Spec.PipelineRunTemplate.Spec.DeepCopy()

		// Make sure name isn't set.
		// TODO(jlewi): Should we allow user to set generateName
		run.Name = ""
		run.GenerateName = modelSync.Name + "-"

		// We don't want to use run.Namespace to run in other namespaces because that could potentially create
		// a path for privelege escalation.
		if run.Namespace != "" {
			log.Info("PipelineRun.Namespace should not be set")
		}
		run.Namespace = modelSync.Namespace

		if err := ctrl.SetControllerReference(modelSync, run, r.Scheme); err != nil {
			return nil, err
		}

		return run, nil
	}

	// If there is already an active run we don't want to submit a new run.
	if len(activeRuns) > 0 {
		return ctrl.Result{}, nil
	}

	// actually make the job...
	run, err := constructRunForModelSync(&modelSync)
	if err != nil {
		log.Error(err, "unable to construct job from template")
		// don't bother requeuing until we get a change to the spec
		scheduledResult := ctrl.Result{RequeueAfter: 1 * time.Minute}
		return scheduledResult, nil
	}

	// ...and create it on the cluster
	if err := r.Create(ctx, run); err != nil {
		log.Error(err, "unable to create PipelineRun for ModelSync", "pipleineRun", run)
		return ctrl.Result{}, err
	}

	log.V(1).Info("created PipelineRun for ModelSync run", "pipelineRun", run)

	return ctrl.Result{}, nil
}

var (
	apiGVStr  = automlv1alpha1.GroupVersion.String()
	ownerKind = "ModelSync"
)

func (r *ModelSyncReconciler) SetupWithManager(mgr ctrl.Manager) error {
	// TODO(jlewi): Add code to initialize GitHub client

	// In order to allow our reconciler to quickly
	// look up PipelineRun by their owner, we'll need an index.  We declare an index key that
	// we can later use with the client as a pseudo-field name, and then describe how to
	// extract the indexed value from the PipelineRun object.  The indexer will automatically take
	// care of namespaces for us, so we just have to extract the owner name if the PipelineRun has
	// a ModelSync owner.

	if err := mgr.GetFieldIndexer().IndexField(&tk.PipelineRun{}, runOwnerKey, func(rawObj runtime.Object) []string {
		// grab the job object, extract the owner...
		job := rawObj.(*tk.PipelineRun)
		owner := metav1.GetControllerOf(job)
		if owner == nil {
			return nil
		}
		// ...make sure it's a CronJob...
		if owner.APIVersion != apiGVStr || owner.Kind != ownerKind {
			return nil
		}

		// ...and if so, return it
		return []string{owner.Name}
	}); err != nil {
		return err
	}

	return ctrl.NewControllerManagedBy(mgr).
		For(&automlv1alpha1.ModelSync{}).
		// Inform the controller that we own pipelineruns so that the reconciler will be invoked if the
		// owned pipelineruns change
		Owns(&tk.PipelineRun{}).
		Complete(r)
}
