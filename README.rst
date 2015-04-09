===============================
tripleo-common
===============================

Management for OpenStack clouds.

* start a new update in interactive mode:

  ``stack-update -s overcloud -t templates/update.yaml -i``

* scale out compute nodes in Overcloud:

  ``stack-scale -s overcloud_stack -p overcloud_plan -n 2 -r Compute-1``
