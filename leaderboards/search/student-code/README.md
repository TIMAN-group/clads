# Student Skeleton Code for a Search Competition

This folder is a barebones example of what a student skeleton repository
might look like for a search competition using the [metapy][metapy] Python
bindings. The important files are:

- `search_eval.py`: this is the file that the students would modify to
   specify their ranker. The `load_ranker()` function should be updated to
   return the desired ranker to use for the competition. It can also be
   executed as a script to run the same ranker on a locally stored dataset
   (this is optional).

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
      specifies the dataset path, query path, and timeout for each dataset.
      Examples are in the `data` folder in the root of this repository.

      Of course, you will also need to upload whatever datasets you wish to
      use to your `/data` share as well. If the competition is purely about
      ranking functions, you can pre-generate the index files and upload
      them into a subfolder of `/data` as well (this is what we did in our
      deployment).

- `.gitlab-ci.yml`: this file specifies the configuration for Gitlab CI;
   you can update this however you'd like, but it shouldn't require any
   changes if `competition.py` is properly updated.

- `timeout.py`: a simple timeout implementation. The goal here is not to be
   undefeatable; rather, it is to just safeguard against bad
   implementations that infinite loop by attempting to bound their
   execution time. This is for accident prevention, not for Machiavellian
   students.

[metapy]: https://github.com/meta-toolkit/metapy
