# `docker-machine` Scripts for Microsoft Azure

The scripts in this folder allow you to spawn an instance of CLaDS in
Microsoft Azure. You will need to follow the instructions here or at [our
website][clads-website] for getting things set up.

## Requirements

- A Microsoft Azure subscription
- A [service principal][service-principal] (you will need the Client ID and
  the Client Secret). Make sure you use "web app" when creating the
  application in the Azure portal, as a "desktop app" will not work
  properly.
- [Docker][docker-install] and [Docker Machine][docker-machine-install]
  both installed locally

**You should ensure that you have some experience using Microsoft Azure
before setting up CLaDS for your class! We are not responsible for any
loss of funds caused by following these instructions or otherwise.** You
should make sure to periodically monitor your subscription utilization to
make sure things are working within expected parameters.

## 1. Scripts and Configuration

First, clone this repository using `git`:

```bash
git clone https://github.com/TIMAN-group/clads.git
```

In the `clads` folder created, you should see an `azure` directory
containing scripts for spawning the required virtual machines for CLaDS on
Microsoft Azure. Navigate to that folder:

```bash
cd clads
cd azure
```

Now, you should set the following environment variables for the scripts:

```bash
export AZURE_SUBSCRIPTION_ID="your-subscription-id-here"
export AZURE_CLIENT_ID="your-client-id-here"
export AZURE_CLIENT_SECRET="your-client-secret-here"
```

This sets the scripts to tie all machines created to the specified
Azure subscription, authenticating with the provided Client ID and Client
Secret.

Next, you will need to determine a proper [Azure Region][azure-regions] to
host your CLaDS instance. Once you've determined this, set an environment
variable as follows:

```bash
export AZURE_LOCATION="westcentralus" # or whatever other region you choose
```

## 2. Spawning the Gitlab CE Server

The first machine we will spawn up is the VCS server. This will be using
Gitlab for its seamless integration with the auto-scaling Gitlab CI tool
that will be used for maintaining the worker cluster.

First, let's create the machine:

```bash
cd gitlab-server
./create-gitlab-server.sh Standard_D2_v2
```

The argument to this script is the [size][azure-size] of the virtual
machine you would like to create. The VCS server handles a lot of I/O load,
so we recommend using a size that does not place a strong limit on IOPS.
Remember, though, that a larger machine will cost more, as the VCS will
always be running. We found a reasonable tradeoff with the D2_v2 size, but
you may also want to try out other sizes.

Running this command will execute `docker-machine` with the correct
arguments to create the virtual machine. This process will take a bit of
time, so be patient. You will see the relevant resources created on the
supplied Azure subscription, a virtual machine created, and Docker
installed on that virtual machine.

## 3. Installing Gitlab

Once the VM is created and the script returns, we can then start
configuring the VM. The first thing you will likely want to do is provide a
hostname to your virtual machine. For now, we will just use the free Azure
subdomain system, but you can also configure your own domain name (this is
outside of the scope of this guide, however).

Log in to the [Azure portal][azure-portal] with your username/password that
is associated with the subscription ID used to create the VM earlier. You
should be able to see it on the dashboard by clicking "All Resources" on
the sidebar, and then look for the virtual machine resource called
"clads-vcs". If you click on it, a new blade should open. On the top, in
the second column should be a heading called "DNS name" with a "Configure"
link below. Click that link, and set a DNS name for your instance, which
will look something like "xxxxxxx.azureregionhere.cloudapp.azure.com".

Let's configure the hostname. Copy the example file:

```bash
cp environment.sh.example environment.sh
```

Now, edit `environment.sh` to have the correct hostname.

Next, let's copy over our scripts to the VCS VM:

```bash
docker-machine scp environment.sh clads-vcs:~
docker-machine scp start-gitlab.sh clads-vcs:~
docker-machine scp reconfigure-gitlab.sh clads-vcs:~
```

Now we are going to install Gitlab into a docker container on that machine.
Get a shell with:

```bash
docker-machine ssh clads-vcs
```

Now you have a shell on the remote VCS server. Let's start a Gitlab
instance now:

```bash
# start the Gitlab container (run these commands *on the remote server*)
source environment.sh
./start-gitlab.sh
```

This will start the installation process for Gitlab in the newly created
container in the background, which will take some time. Eventually, you
should be able to open your web browser and point it at the DNS name you
chose earlier and you should see a page that prompts you to reset your
admin password. **Don't do that yet**; we want to configure Gitlab first.

## 4. Configure Gitlab

On the remote machine, you can edit Gitlab's configuration file like so:

```bash
# on the remote server
sudo vim /srv/gitlab/config/gitlab.rb
```

There are two things you will want to configure here. First, you will
likely want to set up SMTP to allow your Gitlab instance to send email. You
can [follow the guidelines here][gitlab-smtp] to set that up.

Next, you will want to [configure Gitlab to use HTTPS][gitlab-https]. We
recommend following the "Free and automated HTTPS with Let's Encrypt" guide
there; specifically, you'll want to add the following lines:

```ruby
external_url https://YOURHOSTNAME.azureregion.cloudapp.azure.com
letsencrypt['enable'] = true
letsencrypt['contact_emails'] = ['foo@email.com'] # Optional
```

Finally, add the following line to the configuration file:

```ruby
gitlab_rails['gitlab_shell_ssh_port'] = 222
```

Once you've made those changes to the configuration file, you can
reconfigure Gitlab:

```bash
# on the remote server
./reconfigure-gitlab.sh
```

Once this command is complete, you should be all set! You should return to
your browser and refresh the page at your configured DNS name---you should
now be using `https://` in the URL, at which point you can go ahead and set
your initial admin password. Note that the admin user is `root`.

## 5. Configure Dataset Storage

Next, let's configure the storage for our datasets and upload any files we
need to the cloud. We'll start by creating a storage account on the [Azure
portal][azure-portal]. Click on "Storage Accounts" on the side panel. Next,
click the "Add" button. You can name this whatever you'd like, but do make
sure that it is in the same region as your other servers. We recommend
using only "Locally-redundant storage" for the datasets, as our resilience
requirements are not high in this scenario and this is the lowest cost
option. For the resource group, you should be able to use the pre-created
"CLaDS" resource group that was made when we created the VCS server. When
you're done, click the "Create" button.

Once the storage account is created, you should get a notification in the
portal. Click the button to go to the resource, and on this blade you
should see a section called "Files". Click this, and then click the "+ File
share" button in the top left. You can name it whatever you want, and set a
Quota if you'd like.

Once the share is created, you should be able to click on it in the blade
and then add new directories and upload whatever files you would like to
through the Portal UI. Once you've got whatever datasets you would like to
start with uploaded, click the "Connect" button at the top, and navigate
down to the "Connecting from Linux" heading. Copy the command there to your
clipboard and save it somewhere.

## 6. Installing Gitlab CI

Now, let's install Gitlab CI. We're going to follow the recommended setup
and use three things here:

1. The Gitlab CI "bastion" server, which will be in charge of communicating
   with the Gitlab VCS server to coordinate the scheduling of build jobs
   and will create/shrink the worker pool as necessary,
2. A cache server that can be used to store files between build jobs for
   the student repositories, and
3. A Docker registry mirror that can be used to speed up the time it takes
   to fetch the specified Docker image for the build worker to use by
   caching it within the local network

We'll start by creating the last two servers first.

### 6.1. Gitlab CI Cache Server

You can create the cache server as follows (starting from the repository
root folder):

```bash
cd azure
cd gitlab-ci
./create-cache-server.sh Standard_A1_v2
```

This will do the following:

1. Create a virtual machine for the cache server, using a VM of the
   specified size,
2. Start a docker container with the `minio` S3 server,
3. Print out the configuration for that server for use later. Remember the
   Access and Secret Key for later when we configure the Bastion server.

The private IP for the cache server should be configured to be `10.0.0.5`
and will be listening on port `9005`.

### 6.2. Gitlab CI Docker Registry Cache Server

We can now create the Docker registry mirror cache server:

```bash
./create-registry-cache.sh Standard_A1_v2
```

This will do the following:

1. Create a virtual machine for the cache server, using a VM of the
   specified size,
2. Start a docker container to run a registry mirror.

The private IP of the Docker registry mirror cache should be configured to
be `10.0.0.6` and will be listening on port `6000`.

### 6.3 Gitalb CI Bastion Server

Now that we have the two cache servers running, we are ready to set up the
main Gitlab bastion server:

```bash
./create-ci-bastion.sh Standard_A1_v2
```

This will do the following:

1. Create a virtual machine for the CI bastion, using a VM of the specified
   size,
2. Start the runner, and
3. Register the new runner with the system.

The registration process will ask for the following information:

1. gitlab-ci coordinator URL: this is the URL to your VCS server,
2. gitlab-ci token: you can obtain this from the `/admin/runners` page of
   your Gitlab instance,
3. gitlab-ci description: set this to whatever you'd like (this is naming
   the runner),
4. gitlab-ci tags for the runner: leave this empty,
5. whether to lock the runner to the current project: set this to
   **false**,
6. executor: use **docker+machine**,
7. default Docker image: set this to whatever you'd like depending on your
   assignment type (we used `python:3`). Note that this can be changed in
   a project-specific configuration file, so it's not necessarily important
   to be comprehensive with the default choice.

Once this is done, the script should print out your runner's token. Save
this. Now, in the `azure/gitlab-ci` folder of the repository you should
find a `config.toml.example` configuration file. Let's copy it and make our
modifications:

```bash
cp config.toml.example config.toml
vim config.toml
```

We will want to change the following things:

1. `concurrent = XX`: set this to the number of current build jobs you want
   the auto-scaling build cluster to accept. Any jobs beyond this number
   will be shown as "Pending" in the Gitlab UI. This helps serve as an
   upper bound on the number of created worker VMs.
2. `name = "XXXXX"` in the `[[runners]]` block: the name your runner will
   use in the Gitlab interface
3. `url = "XXXXX"` in the `[[runners]]` block: this is he URL (including
   `https://` prefix) to use to communicate with the VCS server
4. `token = "XXXXX"`: the token to use for communication with the VCS
   server; set this to the token we obtained earlier
5. `limit = XX`: set this to the number of concurrent VMs you wish to
   allow, including any idle machines.
6. `image = "XXXXX"`: set this to the desired Docker image for your
   assignments (keep in mind that students can install software during the
   build job as well, so this need not be comprehensive, but pre-installing
   things into a Docker image for them can make things faster)
7. `AccessKey = "XXXXX"`: this is the access key you copied from the cache
   server setup
8. `SecretKey = "XXXXX"`: this is the secret key you copied from the cache
   server setup
9. `IdleCount = XX`: the number of build machines you want to be _always_
   running waiting for build jobs. This is an optimization to eliminate the
   delay associated with creating new build VMs for the first few jobs that
   arrive. This can be set to 0, which will result in zero build machines
   running if there are no pending build jobs.
10. `IdleTime = XXXX`: the amount of time to allow a machine to sit idle
    (in seconds) before it is decomissioned. Setting this higher increases
    the chance that new jobs will use a pre-existing machine, but setting
    it too high may result in a large number of machines sitting idle for
    longer, increasing cost.
11. `MachineOptions = []`: this is an array of options to pass to the
    `docker-machine` commands issued by the runner itself. The settings
    here should be more or less obvious and correspond to the subscription
    id, client id and secret, Azure location, and Azure VM size.

Once you've got that set up how you'd like, there is one last configuration
file to edit: `cloud-init.txt`. This file helps configure the new worker
VMs as they are spawned, and we need to edit this file to properly mount
our shared dataset folder. You will need to replace the
`STORAGEACCOUNTNAME` and `password=XXXXXX` parts of this file with the
correct values for the share you created in step 5.

```bash
cp cloud-init.txt.example cloud-init.txt
vim cloud-init.txt
```

Once these files are properly configured, you will want to upload them to
the remote server:

```bash
./reconfigure-ci.sh
```

This should update the configuration on the remote and the runner should
automatically pick up the new changes in the configuration file.

At this point, you are all set! You can test things out by creating a new
project with a `.gitlab-ci.yml` file; refer to [the Gitlab
documentation][gitlab-ci-docs] for how to set this up.

On the build workers, your file share you created in step 5 will be mounted
_read only_ as `/data`, so the build workers can use any files you have
uploaded to the file share in their build scripts.

## Common Issues

1. I get the following error when reconfiguring Gitlab:

   ```
   Running handlers:
   There was an error running gitlab-ctl reconfigure:

   letsencrypt_certificate[clads-vcs.westcentralus.cloudapp.azure.com] (letsencrypt::http_authorization line 3) had an error: RuntimeError: acme_certificate[staging] (/opt/gitlab/embedded/cookbooks/cache/cookbooks/letsencrypt/resources/certificate.rb line 20) had an error: RuntimeError: ruby_block[create certificate for clads-vcs.westcentralus.cloudapp.azure.com] (/opt/gitlab/embedded/cookbooks/cache/cookbooks/acme/providers/certificate.rb line 100) had an error: RuntimeError: [clads-vcs.westcentralus.cloudapp.azure.com] Certificate request failed: Error creating new cert
   ```

   This can happen if the hostname of the machine matches the prefix of the
   DNS name for the LetsEncrypt setup. Fortunately, resolving this is
   simple. On the remote machine, edit the `/etc/hosts` file. Near the
   bottom, you should see a line like:

   ```
   clads-vcs 127.0.0.1
   ```

   Simply comment out this line by placing a `#` in front, and then re-run

   ```bash
   ./reconfigure-gitlab.sh
   ```

   and the process should complete normally.

2. I get the following error when creating one of the VMs with
   `docker-machine`:

   ```
   Error creating machine: Error running provisioning: Error running "sudo apt-get update": ssh command error:
   ...
   E: can not open /var/lib/apt/lists/archive.ubuntu.com_ubuntu_dists_xenial_InRelease - fopen (2: No such file or directory)
   ```

   A simple workaround is to just retry:

   ```bash
   docker-machine provision MACHINE-NAME-HERE
   ```

   If this succeeds, look at the script you are running and just manually
   run the commands that followed the `docker-machine create` call.

[clads-website]: https://timan-group.github.io/clads/
[service-principal]: https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-group-create-service-principal-portal
[docker-install]: https://www.docker.com/community-edition#/download
[docker-machine-install]: https://docs.docker.com/machine/install-machine/
[azure-regions]: https://azure.microsoft.com/en-us/global-infrastructure/locations/
[azure-size]: https://docs.microsoft.com/en-us/azure/virtual-machines/linux/sizes-general
[azure-portal]: https://portal.azure.com
[gitlab-smtp]: https://docs.gitlab.com/omnibus/settings/smtp.html
[gitlab-https]: https://docs.gitlab.com/omnibus/settings/nginx.html#enable-https
[gitlab-ci-docs]: https://docs.gitlab.com/ce/ci/quick_start/
