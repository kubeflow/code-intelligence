package main

import (
	"flag"
	"fmt"
	"github.com/square/go-jose/v3"
	"github.com/square/go-jose/v3/jwt"
	"io/ioutil"
	"log"
)

type options struct {
	PrivateKey string
	Audience string
}
func main() {
	o := &options{}

	cl := jwt.Claims{}

	flag.StringVar(&o.PrivateKey, "private-key", "/home/jlewi/secrets/chatbot/jwk-sig-chatbot-priv.json", "Path to the private key.")
	flag.StringVar(&cl.Subject, "subject", "dialogflow-webhook", "Subject for the JWT.")
	flag.StringVar(&cl.Issuer, "issuer", "jlewi@google.com", "Issuer of the JWT.")
	flag.StringVar(&o.Audience, "audience", "kubeflow-chatbot", "Audience.")

	cl.Audience = [] string{
		o.Audience,
	}
	keyBytes, err := ioutil.ReadFile(o.PrivateKey)

	if err != nil {
		log.Fatalf("Error reading signing key; error %v", err)
	}

	key := &jose.JSONWebKey{}
	err = key.UnmarshalJSON(keyBytes)

	if err !=  nil {
		log.Fatalf("Error reading signing key; error unmarshaling the key %v", err)
	}

	sig, err := jose.NewSigner(jose.SigningKey{Algorithm: jose.ES256, Key: key}, (&jose.SignerOptions{}).WithType("JWT"))
	if err != nil {
		panic(err)
	}


	raw, err := jwt.Signed(sig).Claims(cl).CompactSerialize()
	if err != nil {
		panic(err)
	}

	fmt.Println(raw)
}