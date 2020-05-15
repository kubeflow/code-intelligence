package pkg


// LabelServiceV1Alpha1 defines an interface suitable for getting information about labels
type LabelServiceV1Alpha1 interface {
	// GetLabelOwners returns a list of owners of the specified label.
	GetLabelOwners(label string)[]string
}
