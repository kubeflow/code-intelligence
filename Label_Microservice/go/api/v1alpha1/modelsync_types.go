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
	tk "github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1"
	corev1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// EDIT THIS FILE!  THIS IS SCAFFOLDING FOR YOU TO OWN!
// NOTE: json tags are required.  Any new fields you add must have json tags for the fields to be serialized.

// ModelSyncSpec defines the desired state of ModelSync
type ModelSyncSpec struct {
	// ModelSelector selects the model to deploy based on labels
	ModelSelector metav1.LabelSelector `json:"modelSelector,omitempty"`

	PipelineRunTemplate PipelineRunTemplate `json:"pipelineRunTemplate,omitempty"`

	// +kubebuilder:validation:Minimum=0

	// The number of successful finished jobs to retain.
	// This is a pointer to distinguish between explicit zero and not specified.
	// +optional
	SuccessfulPipelineRunsHistoryLimit *int32 `json:"successfulPipelineHistoryLimit,omitempty"`

	// +kubebuilder:validation:Minimum=0

	// The number of failed finished jobs to retain.
	// This is a pointer to distinguish between explicit zero and not specified.
	// +optional
	FailedPipelineRunsHistoryLimit *int32 `json:"failedPipelineHistoryLimit,omitempty"`
}

// PipelineRunTemplate is a template for pipeline runs.
type PipelineRunTemplate struct {
	metav1.ObjectMeta `json:"metadata,omitempty" protobuf:"bytes,1,opt,name=metadata"`

	Spec tk.PipelineRunSpec `json:"spec,omitempty"`
}

// ModelSyncStatus defines the observed state of ModelSync
type ModelSyncStatus struct {
	// INSERT ADDITIONAL STATUS FIELD - define observed state of cluster
	// Important: Run "make" to regenerate code after modifying this file

	// A list of pointers to currently running PipelineRuns.
	// +optional
	Active []corev1.ObjectReference `json:"active,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// ModelSync is the Schema for the modelsyncs API
type ModelSync struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata,omitempty"`

	Spec   ModelSyncSpec   `json:"spec,omitempty"`
	Status ModelSyncStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// ModelSyncList contains a list of ModelSync
type ModelSyncList struct {
	metav1.TypeMeta `json:",inline"`
	metav1.ListMeta `json:"metadata,omitempty"`
	Items           []ModelSync `json:"items"`
}

func init() {
	SchemeBuilder.Register(&ModelSync{}, &ModelSyncList{})
}
