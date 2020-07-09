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

package v1alpha1

import (
	"fmt"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/apimachinery/pkg/runtime/schema"
	"k8s.io/apimachinery/pkg/util/validation/field"
	ctrl "sigs.k8s.io/controller-runtime"
	logf "sigs.k8s.io/controller-runtime/pkg/log"
	"sigs.k8s.io/controller-runtime/pkg/webhook"
)

// log is for logging in this package.
var modelsynclog = logf.Log.WithName("modelsync-resource")

func (r *ModelSync) SetupWebhookWithManager(mgr ctrl.Manager) error {
	return ctrl.NewWebhookManagedBy(mgr).
		For(r).
		Complete()
}

// EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!

// +kubebuilder:webhook:path=/mutate-automl-cloudai-kubeflow-org-v1alpha1-modelsync,mutating=true,failurePolicy=fail,groups=automl.cloudai.kubeflow.org,resources=modelsyncs,verbs=create;update,versions=v1alpha1,name=mmodelsync.kb.io

var _ webhook.Defaulter = &ModelSync{}

// Default implements webhook.Defaulter so a webhook will be registered for the type
func (r *ModelSync) Default() {
	modelsynclog.Info("default", "name", r.Name)

	if r.Spec.SuccessfulPipelineRunsHistoryLimit == nil {
		r.Spec.SuccessfulPipelineRunsHistoryLimit = new(int32)
		*r.Spec.SuccessfulPipelineRunsHistoryLimit = 100
	}
	if r.Spec.FailedPipelineRunsHistoryLimit == nil {
		r.Spec.FailedPipelineRunsHistoryLimit = new(int32)
		*r.Spec.FailedPipelineRunsHistoryLimit = 100
	}
}

// TODO(user): change verbs to "verbs=create;update;delete" if you want to enable deletion validation.
// +kubebuilder:webhook:verbs=create;update,path=/validate-automl-cloudai-kubeflow-org-v1alpha1-modelsync,mutating=false,failurePolicy=fail,groups=automl.cloudai.kubeflow.org,resources=modelsyncs,versions=v1alpha1,name=vmodelsync.kb.io

var _ webhook.Validator = &ModelSync{}

// validatePerforms shared validation for create and update.
func (r *ModelSync) validateModelSync() error {
	var allErrs field.ErrorList

	// TODO(jlewi): Could we use declarative validation instead?
	if r.Spec.PipelineRunTemplate.Name != "" {
		allErrs = append(allErrs, field.Invalid(field.NewPath("Spec.PipelineRun.metadata.name"), r.Spec.PipelineRunTemplate.Name, fmt.Sprintf("Spec.PipelineRun.name should not be set; set Spec.PipelineRun.generateName")))
	}

	if r.Spec.PipelineRunTemplate.Namespace != "" {
		allErrs = append(allErrs, field.Invalid(field.NewPath("Spec.PipelineRun.metadata.namespace"), r.Spec.PipelineRunTemplate.Name, fmt.Sprintf("Spec.PipelineRun.namespace should not be set.")))
	}

	if len(allErrs) == 0 {
		return nil
	}

	return apierrors.NewInvalid(
		schema.GroupKind{Group: "batch.tutorial.kubebuilder.io", Kind: "CronJob"},
		r.Name, allErrs)
}

// ValidateCreate implements webhook.Validator so a webhook will be registered for the type
func (r *ModelSync) ValidateCreate() error {
	modelsynclog.Info("validate create", "name", r.Name)

	return r.validateModelSync()
}

// ValidateUpdate implements webhook.Validator so a webhook will be registered for the type
func (r *ModelSync) ValidateUpdate(old runtime.Object) error {
	modelsynclog.Info("validate update", "name", r.Name)

	// TODO(user): fill in your validation logic upon object update.
	return nil
}

// ValidateDelete implements webhook.Validator so a webhook will be registered for the type
func (r *ModelSync) ValidateDelete() error {
	modelsynclog.Info("validate delete", "name", r.Name)

	// TODO(user): fill in your validation logic upon object deletion.
	return nil
}
