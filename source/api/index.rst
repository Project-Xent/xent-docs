API Reference
=============

The C API reference below is generated from the public C23 headers in the
sibling repositories by `Hawkmoth <https://hawkmoth.readthedocs.io/>`__.
Declaration comments specify ownership, ``NULL`` handling, borrowing lifetimes,
threading rules, and error behavior.

- :doc:`core` — Headless layout, node tree, intrinsic/text measurement, and
  display lists (``<xent/xent.h>``), used when building custom hosts or headless
  layout pipelines.
- :doc:`kit` — Atomic ``XtkBatch`` protocol, retained ``XtkHost`` ABI, event
  payloads, and reconciler runtime (``<xtk/...>``). Declarative element builders
  are declared in ``<xtk/xtk.h>``; generated imperative control wrappers are
  declared in ``<xtk/xtk_controls.h>``.
- :doc:`fluxent` — Native Windows application entry points (``flux_run``,
  ``FluxApp``), ``XtkHost`` attachment, windowing, menus, popups, file dialogs,
  clipboard, and drag-and-drop (``<fluxent/...>``).

.. toctree::
   :maxdepth: 1

   core
   kit
   fluxent
