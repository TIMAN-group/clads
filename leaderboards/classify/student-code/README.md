# Student Skeleton Code for a Search Competition

This folder is a barebones example of what a student skeleton repository
might look like for a search competition using the [metapy][metapy] Python
bindings. The important files are:

- `classify.py`: this is one of the files that students would modify to
   specify their classifier. The `make_classifier()` function should be
   updated to return their desired classifier to use fo rthe competition.
   It can also be executed as a script to run the same classifier on a
   locally stored dataset (this is optional).

- `config.toml`: this is a configuration file for MeTA that dictates how
   the data is pre-processed into feature vectors; students can update this
   file to add/change feature types used for their document representation.

- `competition.py`: this is the script that is run on the build worker to
   assemble the results to a set of queries to then be evaluated by the
   leaderboard. Before releasing to students, you will want to do the
   following:

   1. Ensure that the `submission_url` variable is updated properly to use
      the correct internal IP for the leaderboard server
   2. Set `top_k` to the number of results that should be returned for each
      query for evaluation purposes
   3. Update the `cfgs` array to be an array of files accessible on the
      build workers (we suggest placing them in the `/data` share) that
      specifies the dataset path, training/testing data split, and timeout
      for each dataset. Examples are in the `data` folder for the
      leaderboard.

      Of course, you will also need to upload whatever datasets you wish to
      use to your `/data` share as well. We recommend uploading a
      "withheld" version of the dataset where the labels for the testing
      portion of the documents have been redacted.

- `.gitlab-ci.yml`: this file specifies the configuration for Gitlab CI;
   you can update this however you'd like, but it shouldn't require any
   changes if `competition.py` is properly updated.

- `timeout.py`: a simple timeout implementation. The goal here is not to be
   undefeatable; rather, it is to just safeguard against bad
   implementations that infinite loop by attempting to bound their
   execution time. This is for accident prevention, not for Machiavellian
   students.

# Instructions for Students
The students will need to do some setup to configure their desired name on
the leaderboard (defaults to "Anonymous") as well as tie their results to
their Gitlab username (for grading purposes).

## Competition Setup
This is a two-step process. First, we'll make an access token for your user
(this is submitted along with the competition results for authentication),
and then set the needed pipeline variables to submit your results to the
leaderboard.

### Making an Access Token
Go to the upper right hand corner and click the drop-down and go to
"Settings". From there, go to "Access Tokens". Create a new token (it can
be called whatever you'd like, but I used "Competition API"), and give it
the **read_user** scope. Then, click "Create personal access token". There
will be a box at the top of the screen that appears with the access token.
**Make sure to copy this to your clipboard as you won't be able to see it
again!**

### Configuring Pipeline Variables
Now that you have your access token copied to your clipboard, go back to
your fork of the repository. Click on "Settings", and then "Pipelines".
Look for the "**Secret variables**" section. We'll need to add two
variables. The first will be called `GITLAB_API_TOKEN`. Set the value to
the access token you copied before.

Finally, create another variable called `COMPETITION_ALIAS` and set that to
whatever you'd like your entry to be named on the leaderboard.

Once both of these variables are set, you should be ready to go! Each push
to this repository should start a build job that runs your code and submits
the results to the leaderboard to be judged.

[metapy]: https://github.com/meta-toolkit/metapy
