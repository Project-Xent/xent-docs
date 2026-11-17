Quick Start
===========

This guide walks through installing the C23 toolchain on Windows, adding the
official project templates, choosing between the **declarative** and
**imperative** tracks, and building and running your first **Xent 0.3.3**
application.

Step 1: Install the Toolchain
-----------------------------

Building a Xent C application on Windows requires **Windows 10 version 1903 or
later**, ``git``, **Xmake 3.1.2+**, and the **llvm-mingw** C23 compiler
toolchain.

1. **Install Xmake (3.1.2 or newer)**: Follow the official `Xmake Installation
   Guide <https://xmake.io/guide/quick-start.html>`__, and install `Git
   <https://git-scm.com/>`__ so Xmake can fetch package repositories.
2. **Install llvm-mingw (UCRT)**: Xent uses ``llvm-mingw`` Clang as its primary
   C23 toolchain on Windows. Visit `mstorsjo/llvm-mingw
   <https://github.com/mstorsjo/llvm-mingw>`__ and download the latest
   Windows-native **UCRT** ``.zip`` archive for your architecture from
   `llvm-mingw Releases <https://github.com/mstorsjo/llvm-mingw/releases>`__:

   - 64-bit x86 Windows: ``llvm-mingw-<date>-ucrt-x86_64.zip``
   - Windows on ARM: ``llvm-mingw-<date>-ucrt-aarch64.zip``

   Extract the archive to a permanent directory (for example ``C:\llvm-mingw``)
   and add its ``bin`` folder (``C:\llvm-mingw\bin``) to your user ``PATH``.

Open a new terminal window and verify that all three commands report their
versions:

.. code-block:: powershell

   xmake --version
   git --version
   x86_64-w64-mingw32-clang --version

Step 2: Install the Project Templates
-------------------------------------

Project Xent distributes ready-to-build C23 project templates as an `Xmake Addon
<https://xmake.io/guide/extensions/addons/installation.html>`__. Install the
``xent-repo`` addon once for your user account and list the available templates:

.. code-block:: powershell

   xmake addon -i github:Project-Xent/xent-repo
   xmake create --list

Under language ``c``, two Fluxent templates are available:

- ``fluxent.decl`` — Declarative application (``flux_run``)
- ``fluxent.imp`` — Imperative application (``XtkScene`` / ``XtkTxn``)

Step 3: Declarative vs. Imperative — Comparison & How to Choose
---------------------------------------------------------------

Both ``fluxent.decl`` and ``fluxent.imp`` share the same retained Fluxent host,
native Direct2D/DirectWrite controls, accessibility support, and atomic
``XtkBatch`` commit engine. Pick the track whose programming model fits your
application:

.. list-table::
   :header-rows: 1
   :widths: 20 40 40

   * - Dimension
     - Declarative (``fluxent.decl``)
     - Imperative (``fluxent.imp``)
   * - **Programming model**
     - Unidirectional Model–View–Update (MVU) loop driven by ``flux_run``.
     - Retained ``XtkScene`` handles, atomic ``XtkTxn`` transactions, and C
       event callbacks.
   * - **Entry point & headers**
     - ``flux_run(&cfg, &model, update, view)`` with ``<fluxent/fluxent.h>``
       and ``<xtk/xtk.h>`` builders.
     - ``flux_app_create`` + ``flux_app_attachhost`` + ``xtk_scene_fromhost``
       with ``<xtk/xtk_controls.h>``.
   * - **UI construction & updates**
     - ``view()`` returns a lightweight ``XtkEl *`` tree derived from ``Model``;
       the reconciler computes and commits the minimal ``XtkBatch`` diff
       automatically.
     - Your code opens an ``XtkTxn``, calls typed ``xtk_*_create`` functions
       with ``.set`` bitmasks, saves ``XtkCtrl`` handles, and calls
       ``xtk_*_set*`` setters directly.
   * - **Event handling**
     - Controls post ``XtkMsg`` values; state transitions live in a single
       ``update(model, msg)`` function.
     - Controls invoke ``XtkEventFn`` callbacks attached via ``xtk_*_on*`` or
       ``xtk_txn_on``; callbacks mark state dirty and update target controls.
   * - **Strengths**
     - Concise code; automatic synchronization between state and UI; automatic
       control lifetime management; straightforward conditional layouts.
     - Direct per-property writes; explicit control over transaction boundaries
       and ``XtkCtrl`` lifetimes; stable C ABI used by language bindings.
   * - **Considerations**
     - Evaluates ``view()`` after message batches (use ``xtk_memo_region`` or
       ``xtk_static_region`` to cache large unchanging subtrees).
     - Requires explicit ``.set`` property bitmasks, ``XtkLocalId`` to
       ``XtkCtrl`` handle resolution, and manual UI state updates.

How to Choose
~~~~~~~~~~~~~

- **Choose Declarative (** ``fluxent.decl`` **) as the default** when starting
  with Xent or building desktop applications, forms, settings panels, multi-step
  wizards, and developer tools.
- **Choose Imperative (** ``fluxent.imp`` **)** when integrating Xent into an
  existing callback- or tick-driven C engine, issuing high-frequency targeted
  property writes per frame, or writing a foreign-language binding over Xent's C
  ABI.

Step 4: Create, Install Dependencies, Build, and Run Your First App
-------------------------------------------------------------------

Create a new project from your chosen template (use ``-t fluxent.decl`` for
declarative, or ``-t fluxent.imp`` for imperative):

.. code-block:: powershell

   xmake create -l c -t fluxent.decl hello
   cd hello

This generates ``xmake.lua`` and ``src/main.c`` configured for C23, the
``xent-repo`` package repository, and the Windows GUI subsystem.

Configure Xmake with the root directory of your extracted ``llvm-mingw``
installation (the parent folder containing ``bin``, such as ``C:\llvm-mingw``):

.. code-block:: powershell

   xmake f -p mingw -a x86_64 --mingw="C:\llvm-mingw" -m debug -y

*(On ARM64 Windows, pass* ``-a arm64`` *.)*

Install the dependencies declared in ``xmake.lua``—``xmake require`` downloads
and builds ``fluxent 0.3.3`` together with ``xent-kit 0.3.3``, ``xent-core
0.3.3``, and ``cwinrt 0.3.1``:

.. code-block:: powershell

   xmake require

.. tip::

   The initial ``xmake require`` compiles all four packages from source and
   caches them locally. Run ``xmake require --list`` at any time to view the
   installed packages and versions.

Build and run the application:

.. code-block:: powershell

   xmake
   xmake run

A native Mica-styled window titled **hello** opens with a ``Counter`` heading,
``Value: 0``, and ``−``, ``+``, and ``Reset`` buttons. After editing
``src/main.c``, run ``xmake`` and ``xmake run`` to rebuild incrementally; run
``xmake require`` again whenever you update ``add_requires`` in ``xmake.lua``.

Next Steps
----------

Continue with the guide for your track:

- :doc:`declarative` — Learn the Elm MVU loop, walk through the
  ``fluxent.decl`` template, and work with layout containers, ``xtk_fmt``,
  inputs, and virtualized lists.
- :doc:`imperative` — Walk through the ``fluxent.imp`` template, ``XtkScene``,
  atomic ``XtkTxn`` transactions, ``.set`` property bitmasks, and event
  callbacks.
- :doc:`concepts` — Understand how ``xent-core``, ``xent-kit``, and ``fluxent``
  fit together, and how ``flux_controls_use`` keeps executables small.
