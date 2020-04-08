*******************************
GitLab CI configuration details
*******************************

When running on the APK Foundry executor, there are a few notes to take
into account:

* The ``script:`` key is run within the container once for each package
  to be built. The working directory is set to the git repository root
  (``/af/aports``), and ``$1`` is set to the startdir that needs to be
  built currently (e.g. ``system/debianutils``).
* Due to how executors are implemented in GitLab runner,
  ``before_script:`` is run from the same shell script as ``script:``,
  and thus is run once per package build inside the container with
  ``/af/aports`` as the working directory.
* ``after_script:`` is run regardless of the success of all the package
  builds, from a separate shell script inside the container after they
  all have been attempted.
* Stage job, and tag names are all completely arbitrary.
* Since GitLab runner only allows uploading artifacts from within
  ``GIT_CLONE_PATH``, a symlink ``.gl-repos`` is provided in the git
  repository root pointing to ``REPODEST`` for your convenience.

Variables
---------

================== =====================================================
     Variable                              Notes
================== =====================================================
``CI_BUILDS_DIR``  This is the directory root for the container. Inside
                   the container it will be ``/``.
``GIT_CLONE_PATH`` This must be set to ``$CI_BUILDS_DIR/af/aports``.
``AF_ARCH``        The architecture for which this job will build.
``AF_PACKAGES``    List of packages to manually include in the build.
``AF_PRIVKEY``     Name of the private key with which to re-sign packages
                   outside of the container. These are stored in
                   ``/etc/apkfoundry/$project/`` on each builder.
``AF_PRIVKEY_B64`` Base64-encoded form of the packager private key used
                   to re-sign packages outside of the container.
``AF_PUBKEY``      Name to use for the package signature (customarily
                   ends in ``.pub``; this must match the filename in
                   ``/etc/apk/keys``)
================== =====================================================

Example .gitlab-ci.yml
----------------------

.. code-block:: yaml

    stages:
      - af-builds

    .af-build:
      stage: af-builds

      variables:
        GIT_CLONE_PATH: $CI_BUILDS_DIR/af/aports

      before_scirpt:
        # configure: error: GNAT is required to build ada
        - case "$1" in
          system/gcc) $SUDO_APK add -t .makedepends-gcc-self gcc-gnat;;
          esac

      script:
        - cd "$1"
        - abuild -r

      artifacts:
        paths:
          - .gl-repos/*/*/*.apk
          - .gl-repos/*/*/APKINDEX.tar.gz

    .af-x86_64-build:
      extends: .af-build
      variables:
        AF_ARCH: x86_64
      tags:
        - af-x86_64

    .af-pmmx-build:
      extends: .af-build
      variables:
        AF_ARCH: pmmx
      tags:
        - af-pmmx

    master-x86_64-build:
      extends: .af-x86_64-build
      only:
        - master

    master-pmmx-build:
      extends: .af-pmmx-build
      only:
        - master

    MR-x86_64-build:
      extends: .af-x86_64-build
      only:
        - merge_requests
      artifacts:
        when: always

    MR-pmmx-build:
      extends: .af-pmmx-build
      only:
        - merge_requests
      artifacts:
        when: always