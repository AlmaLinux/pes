# Quick overview

* [Requirements](#Requirements)
* [How to deploy](#Deploying)

## Requirements

* AlmaLinux 8 (target server)
* Ansible version is 2.10 or newer
* Ansible community.docker collection
    * Use command `ansible-galaxy collection install community.docker` for installing it

## Deploying

1. Clone GitHub repo `https://github.com/AlmaLinux/pes.git`
2. Go to project directory `ci/ansible/inventory`
3. Copy template inventory `template` to a new file
4. Fill the following items
    1. In section `pes` place an IP of server for deploying
    2. Set value of option `container_env_prefix` to `prod` in case of production layout or `dev` in other cases.
    3. Set value of option `sentry_dsn` to your DSN key of a Sentry. 
       Skip this step if you don't have this key
    4. Set value of option `deploy_environment` to `Production` if you deploy 
       production variant of the service. Otherwise, use `Dev` or something like this.
    5. Set value of option `flask_secret_key` to random string. E.g. `124120bydf978g6sd9fg`
    6. Create a GitHub OAuth application, take a client ID and a client secret from it and fill options `github_client_id` and `github_client_secret`
    7. Set value of option `backend_port` to value of port which will be used 
       for proxying requests from nginx to container. The container will 
       accept only local connections if you set value of `deploy_environment` to `Production`. 
       Otherwise, the container will accept remote connections. 
    8. Set value of options `uwsgi_address` and `uwsgi_port`. Those are used for starting uwsgi service inside a container.
    9. Set value of option `domain` if you want to use https on your server
    10. Set value of option `postgres_password` and don't change it in the future
5. Go to project directory `ci/ansible`
6. Run command `ansible-playbook -vv -i inventory/<new_inventory_file_name> -u 
   <username> --become main.yml`, there is `<username>` is name of a user from a remote server which has sudo rights
