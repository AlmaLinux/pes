# starts automatically in
# docker container before uwsgi start
# as mentioned here: https://github.com/tiangolo/uwsgi-nginx-flask-docker
python db/db_actions.py create_db
python db/db_actions.py migrate
