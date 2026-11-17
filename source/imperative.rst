Imperative UI Guide
===================

On the **imperative track** (``fluxent.imp``), your application drives a
retained ``XtkScene`` directly through atomic ``XtkTxn`` transactions, typed
control helpers in ``<xtk/xtk_controls.h>``, and C event callbacks.

.. note::

   The imperative API is also Xent's stable C binding surface: ``oxent``,
   ``zxent``, ``xenthon``, and ``hsxent`` all build on these functions.

Anatomy of the ``fluxent.imp`` Template
---------------------------------------

Running ``xmake create -l c -t fluxent.imp hello`` scaffolds an imperative
counter application in ``src/main.c``:

.. code-block:: c

   #include <fluxent/fluxent.h>
   #include <fluxent/flux_app.h>
   #include <fluxent/flux_host.h>
   #include <xtk/xtk_controls.h>

   #include <stdio.h>

   #define LIT(s) .text = s, .text_len = sizeof(s) - 1

   typedef struct Counter {
       FluxApp *app;
       XtkScene scene;
       XtkCtrl  value;
       int      n;
       bool     dirty;
   } Counter;

   static uint32_t bump(Counter *c, int n) {
       c->n     = n;
       c->dirty = true;
       flux_app_redraw(c->app);
       return XTK_EVENT_HANDLED;
   }

   static uint32_t on_inc(void *arg, XtkEvent const *e) {
       (void) e;
       Counter *c = arg;
       return bump(c, c->n + 1);
   }

   static void frame(void *arg) {
       Counter *c = arg;
       if (!c->dirty) return;
       c->dirty = false;
       char buf[32];
       int  len = snprintf(buf, sizeof(buf), "Value: %d", c->n);
       xtk_text_settext(&c->scene, c->value, buf, (uint32_t) len, (XtkChangeStamp) {});
   }

Core Lifecycle: App, Host, and Scene
------------------------------------

An imperative Fluxent program initializes three core objects in ``WinMain``:

1. **Register control modules**: Call ``flux_controls_use(&flux_ctrl_<name>)``
   for each control type your program creates (such as ``&flux_ctrl_container``,
   ``&flux_ctrl_text``, ``&flux_ctrl_button``), or ``flux_controls_all()`` to
   register the full catalog.
2. **Create the window app**: ``FluxApp *app = flux_app_create(&cfg);`` sets up
   the Win32 window, Direct2D/DirectWrite device resources, and input pipeline.
3. **Attach the retained Host and wrap a Scene**:

   .. code-block:: c

      XtkHost *host = flux_app_attachhost(app);
      XtkScene scene = xtk_scene_fromhost(host);

   ``XtkHost`` owns the live controls and validates batches; ``XtkScene`` is a
   lightweight value handle passed to ``xtk_txn_*`` and ``xtk_<ctrl>_*``
   functions.
4. **Run and shut down in reverse order**: Build your initial control tree, run
   the event loop with ``flux_app_run(app)``, clear any frame callback with
   ``flux_app_onframe(app, NULL, NULL)``, destroy the host via
   ``flux_host_destroy(host)``, and destroy the app via
   ``flux_app_destroy(app)``.

Building Controls with Atomic Transactions (``XtkTxn``)
-------------------------------------------------------

Tree mutations—creating controls, inserting/moving/dropping nodes, and attaching
initial event listeners—execute inside an ``XtkTxn`` transaction. The host
validates and commits the entire transaction atomically so every operation
succeeds together.

1. Begin a Transaction
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: c

   XtkTxn txn;
   if (!xtk_txn_begin(&scene, &txn)) return false;

2. Create Controls with ``.set`` Property Bitmasks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because ``0`` is a valid value for numeric and enum properties in C, typed
``Xtk<Ctrl>Props`` structs in ``<xtk/xtk_controls.h>`` pair property fields with
an explicit ``.set`` bitmask indicating which properties to apply:

.. code-block:: c

   XtkLocalId col_id = xtk_container_create(
       &txn,
       xtk_ref_existing(xtk_scene_root(&scene)),
       &(XtkContainerProps) {
           .set   = XTK_CONTAINER_DIR_MASK | XTK_CONTAINER_GROW_MASK | XTK_CONTAINER_GAP_MASK,
           .dir   = XTK_STACK_COLUMN,
           .grow  = 1.0f,
           .gap   = 16.0f,
       }
   );

.. important::

   Include the corresponding ``XTK_<CTRL>_<PROP>_MASK`` bit in ``.set`` for
   every property field you assign. String properties take explicit pointer and
   UTF-8 byte-length pairs (for example ``.text`` and ``.text_len``).

3. Reference Controls via ``XtkNodeRef``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Within an open transaction, ``xtk_*_create`` functions return a batch-local
``XtkLocalId``, and operations accepting a parent or target take an
``XtkNodeRef``:

- ``xtk_ref_existing(ctrl)`` — References an already-committed ``XtkCtrl`` (such
  as ``xtk_scene_root(&scene)``).
- ``xtk_ref_local(local_id)`` — References a control created earlier in the same
  ``XtkTxn``.
- ``xtk_ref_none()`` — Null reference (used as ``before`` when appending to the
  end of a container).

4. Commit and Extract Persistent ``XtkCtrl`` Handles
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For any control you plan to update later (such as the ``Value: 0`` text node),
map its ``XtkLocalId`` to a generation-checked ``XtkCtrl`` handle from the
``XtkBatchResult *`` returned by ``xtk_txn_commit``:

.. code-block:: c

   XtkBatchDiag diag = {0};
   XtkBatchResult *result = xtk_txn_commit(&txn, &diag);
   if (!result) {
       // Inspect diag.error, diag.op_index, diag.control, diag.property when debugging
       return false;
   }

   for (uint32_t i = 0; i < result->control_count; i++) {
       if (result->controls[i].local == value_local_id) {
           c->value = result->controls[i].control;
       }
   }
   xtk_batchresult_destroy(result);

Release every non-NULL ``XtkBatchResult *`` with ``xtk_batchresult_destroy``. To
discard an open transaction prior to commit, call ``xtk_txn_abort(&txn)``.

Subscribing to Events
---------------------

Generated helpers in ``<xtk/xtk_controls.h>`` register typed event callbacks
inside a transaction:

.. code-block:: c

   xtk_button_oninvoke(&txn, xtk_ref_local(btn_id), on_inc, c);

For custom phase routing (``XTK_EVENT_PHASE_MASK_CAPTURE``, ``TARGET``,
``BUBBLE``) or dynamic subscriptions, use ``xtk_txn_on`` inside a transaction or
``flux_host_subscribe`` on the host.

Event Callback Conventions
~~~~~~~~~~~~~~~~~~~~~~~~~~

An ``XtkEventFn`` uses the signature:

.. code-block:: c

   uint32_t on_event(void *arg, XtkEvent const *event);

- Read typed event data from ``event->payload`` (``u.b``, ``u.i32``, ``u.f32``,
  ``u.f64``, ``u.string``, ``u.window``, ``u.scroll``).
- Copy string slices in ``event->payload.u.string`` and ``u.query`` during the
  callback whenever you need to retain them afterwards.
- Return ``XTK_EVENT_HANDLED`` (optionally combined with flags from
  ``XtkEventDisposition`` such as ``XTK_EVENT_STOP_PROPAGATION``) when handled,
  or ``XTK_EVENT_CONTINUE`` (``0``) to continue routing.

Coalescing Updates with Frame Callbacks
---------------------------------------

To update a single property on a committed ``XtkCtrl`` from the UI thread, call
the generated typed setter (such as ``xtk_text_settext(&scene, ctrl, buf, len,
stamp)``) or the generic ``xtk_ctrl_set*`` helpers in ``<xtk/xtk_scene.h>``.

When several input events arrive before the next vertical blank, coalesce UI
writes using ``flux_app_onframe`` as shown in the ``fluxent.imp`` template:

1. Register a frame callback once via ``flux_app_onframe(app, frame, &state)``.
2. Inside event callbacks, update your C struct, set ``dirty = true``, and call
   ``flux_app_redraw(app)``.
3. Inside ``frame()``, flush the updated properties right before rendering.

Pass a zero-initialized ``(XtkChangeStamp) {0}`` for ordinary programmatic
writes.

Browsing Imperative Examples
----------------------------

The ``fluxent`` repository provides a complete imperative implementation of the
Control Gallery under ``examples/gallery_imp/``. Run
``xmake run fluxent_gallery_imp`` inside a ``fluxent`` checkout to explore every
control and compare it alongside ``examples/gallery_decl/``.
