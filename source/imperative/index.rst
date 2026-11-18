Imperative UI Guide
===================

The **imperative track** (``fluxent.imp``) gives your C23 program direct
ownership over a retained ``XtkScene``, atomic ``XtkTxn`` transactions,
generated typed control wrappers in ``<xtk/xtk_controls.h>``, and routed
``XtkEventFn`` callbacks.

The imperative API is also Xent's stable C ABI surface: ``oxent`` (Rust),
``zxent`` (Zig), ``xenthon`` (Python), and ``hsxent`` (Haskell) all compile down
to these functions.

Read the six chapters in sequence to go from basic window startup to
100,000-row virtualized collections and OS shell integration:

1. :doc:`lifecycle` — Initialize control modules, ``FluxApp``, ``XtkHost``, and
   ``XtkScene``, dissect the ``fluxent.imp`` template, and shut down cleanly.
2. :doc:`transactions` — Build, reparent, reorder, and swap dynamic page
   subtrees atomically with ``XtkTxn``, ``XtkNodeRef``, ``XtkBatchResult``, and
   ``XtkBatchDiag``.
3. :doc:`properties` — Master ``<xtk/xtk_controls.h>`` ``.set`` bitmasks,
   string length conventions, reusable Flex layout helpers, generic property
   queries, and composite data setters.
4. :doc:`events` — Subscribe to capture/target/bubble event phases, decode
   ``XtkEventPayload`` variants, coalesce per-frame UI syncs with
   ``flux_app_onframe``, and coordinate controlled inputs with
   ``XtkChangeStamp``.
5. :doc:`virtualization` — Drive 100,000-row ``ListView`` and ``GridView``
   controls imperatively via ``XTK_EVENT_REALIZE``, slot recycling, and sticky
   group headers.
6. :doc:`shell` — Control modal ``ContentDialog`` instances, open native file
   dialogs, handle ``FluxData`` clipboard and drag-and-drop payloads, customize
   window chrome, and marshal worker-thread callbacks.

.. toctree::
   :maxdepth: 2

   lifecycle
   transactions
   properties
   events
   virtualization
   shell
