# Code Intelligence Operations log

* This is a running log of operations and infrastructure management
  related to Kubeflow code intelligence.

* Enteries should be time stamped and in reverse chronological order (more recent at the top)


## 2020-05-15 - Create an ASM cluster for the Kubeflow chatbot.

* A cluster with ISTIO 1.4 is needed in order to work with Dialogflow. 

  * jlewi@ tried an ISTIO 1.1. cluster but was hitting problems with JWT validation.


* The configs for the new cluster are in ./kubeflow_clusters/code-intelligence

