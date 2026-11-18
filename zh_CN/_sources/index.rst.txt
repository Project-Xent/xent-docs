Project Xent
============

Project Xent is a native cross-platform UI stack written in C23 (current
release **0.3.3**). Application code runs against a platform-neutral control
protocol while a native host provides OS windowing, text shaping, input
handling, and accessibility.

Stack Overview
--------------

Project Xent consists of three C23 packages. Application code works directly
with ``xent-kit`` and the target platform host (``fluxent`` on Windows):

.. list-table::
   :header-rows: 1
   :widths: 20 24 56

   * - Package
     - Application Usage
     - Responsibilities
   * - ``xent-core``
     - Pulled automatically as a dependency
     - Platform-neutral layout engine (Flex, Grid, SwiftStack, Absolute),
       generation-checked node tree, intrinsic and text measurement caches,
       semantics, and immutable display lists.
   * - ``xent-kit``
     - ``<xtk/xtk.h>`` or ``<xtk/xtk_controls.h>``
     - Standard control catalog, atomic ``XtkBatch`` transaction protocol,
       imperative ``XtkScene`` API, and the declarative ``xtk_*`` runtime.
   * - ``fluxent``
     - ``<fluxent/fluxent.h>``
     - Native Windows 10 1903+ host built on Win32, Direct2D, DirectWrite,
       DirectComposition, UI Automation, and ``cwinrt``. Manages windows,
       Fluent control rendering, Mica/Acrylic backdrops, IME, input, and the
       application event loop (``flux_run`` / ``flux_app_run``).

.. note::

   Official **0.3.3** language bindings share the same control catalog and host:
   ``oxent`` (Rust), ``zxent`` (Zig), ``xenthon`` (Python 3.12+), and ``hsxent``
   (Haskell). This manual covers the C23 stack.

.. toctree::
   :maxdepth: 2
   :caption: Manual

   quickstart
   declarative/index
   imperative/index
   concepts
   api/index
