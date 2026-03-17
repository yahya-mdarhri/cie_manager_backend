
docker build --platform=linux/amd64 -t registry.heroku.com/ciemanagerbackend/web . --provenance=false
docker push registry.heroku.com/ciemanagerbackend/web
heroku container:release web --app  ciemanagerbackend 
heroku open --app  ciemanagerbackend 

