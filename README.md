# Introduction

For the purposes of not having to scour Google, StackOverflow, and various forums again, I've written this simple
multi-container app that demonstrates:

- docker-compose
- Dockerfiles
- docker network DNS
- compose multi-container load balancing via reverse proxy
- accessing a cache via DNS host resolution

My hope is that this is useful to others who are on the same learning path I am.

# Contributing

If this demonstrative app is useful to you and you have recommendations of how to
improve it, please consider opening a pull request!

If an extension of functionality is recommended that makes the application more difficult
to understand for a beginner, I'd like to separate the applications into separate sub-folders.
To be handled in the future, however.

## Author

James Kunstle; jkunstle@redhat.com or jskunstle@gmail.com


Notes:

- make sure that the flask apps are running on host '0.0.0.0' otherwise nothing can connect to them.
- the nginx configuration for location '/' routes to all subdomains as well.
