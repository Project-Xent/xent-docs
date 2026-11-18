2. Atomic Transactions & Dynamic Subtrees
=========================================

All structural changes to a retained ``XtkScene``—creating controls, dropping
subtrees, inserting, reordering, reparenting, and binding event listeners—happen
inside an ``XtkTxn`` transaction declared in ``<xtk/xtk_scene.h>``.

All-or-Nothing Commit Guarantee
-------------------------------

When you call ``xtk_txn_commit(&txn, &diag)``, the host executes four stages
(``VALIDATE``, ``PREFLIGHT``, ``PREPARE``, ``COMMIT``):

- Every handle generation, parent-child cycle rule, registered control type,
  property type, and memory allocation is verified before the live tree is
  mutated.
- When validation and preparation succeed, all operations take effect together
  and ``xtk_scene_revision(&scene)`` advances.
- When any operation fails, ``xtk_txn_commit`` returns ``NULL``, fills the
  optional ``XtkBatchDiag`` struct, and leaves the live ``XtkScene`` untouched.

Transaction Operations Overview
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 36 64

   * - Function
     - Purpose
   * - ``xtk_txn_begin(&scene, &txn)``
     - Opens a fresh transaction backed by a new ``XtkBatch``.
   * - ``xtk_<ctrl>_create(&txn, parent, &props)``
     - Typed control creation from ``<xtk/xtk_controls.h>``; appends the new
       control to ``parent`` and returns an ``XtkLocalId``.
   * - ``xtk_txn_create(&txn, type, parent, before, patches, count)``
     - Low-level creation for any ``XtkCtrlId`` (such as ``XTK_CTRL_LISTITEM``
       or ``XTK_CTRL_GROUPHEADER``) with explicit ``before`` positioning.
   * - ``xtk_txn_insert(&txn, parent, child, before)``
     - Inserts an unparented node before ``before`` (or at the end when
       ``before`` is ``xtk_ref_none()``).
   * - ``xtk_txn_move(&txn, parent, child, before)``
     - Reorders ``child`` among siblings under its current ``parent``.
   * - ``xtk_txn_reparent(&txn, child, new_parent, before)``
     - Moves ``child`` from its existing parent into ``new_parent``.
   * - ``xtk_txn_drop(&txn, target)``
     - Destroys ``target`` and its entire descendant subtree, automatically
       removing its event subscriptions and invalidating old ``XtkCtrl``
       generations.
   * - ``xtk_txn_commit(&txn, &diag)``
     - Atomically commits the batch and returns a heap-allocated
       ``XtkBatchResult *`` (or ``NULL`` on error).
   * - ``xtk_txn_abort(&txn)``
     - Discards an uncommitted transaction and frees its internal batch buffer.

Addressing Nodes with ``XtkNodeRef``
------------------------------------

Inside an open ``XtkTxn``, you frequently mix existing committed controls (like
``xtk_scene_root(&scene)``) with controls that were just created two lines above
and only have a batch-local ``XtkLocalId``. ``XtkNodeRef`` unifies both:

- ``xtk_ref_existing(ctrl)`` — Wraps a live, generation-checked ``XtkCtrl`` from
  an earlier commit.
- ``xtk_ref_local(local_id)`` — Wraps an ``XtkLocalId`` created earlier in the
  **current** ``XtkTxn``.
- ``xtk_ref_none()`` — Represents "no node" (used as ``before`` to append at the
  end of a child list).

Resolving ``XtkLocalId`` to ``XtkCtrl`` After Commit
----------------------------------------------------

Static labels, containers, and dividers rarely need to be touched again after
creation—you can ignore their ``XtkLocalId`` once their children are attached.
For controls whose properties you will update later, extract their persistent
``XtkCtrl`` handle from ``XtkBatchResult``:

.. code-block:: c

   static XtkCtrl resolve_ctrl(XtkBatchResult const *res, XtkLocalId local) {
       if (local == XTK_LOCAL_INVALID) return XTK_CTRL_INVALID;
       for (uint32_t i = 0; i < res->control_count; i++) {
           if (res->controls[i].local == local) {
               return res->controls[i].control;
           }
       }
       return XTK_CTRL_INVALID;
   }

Always release a non-NULL ``XtkBatchResult *`` with
``xtk_batchresult_destroy(result)`` once you finish reading ``result->controls``
and ``result->subscriptions``.

Diagnosing Rejected Batches with ``XtkBatchDiag``
-------------------------------------------------

During development, pass an ``XtkBatchDiag`` to ``xtk_txn_commit`` so any
rejected batch immediately tells you which operation failed and why:

.. code-block:: c

   XtkBatchDiag    diag   = {0};
   XtkBatchResult *result = xtk_txn_commit(&txn, &diag);
   if (!result) {
       fprintf(stderr, "Batch failed: error=%d stage=%d op=%u\n",
               (int) diag.error, (int) diag.stage, diag.failed_op);
       return false;
   }

Common ``diag.error`` causes:

- ``XTK_BATCH_ERR_BACKEND`` — A control's ``FluxControlModule`` was omitted from
  ``flux_controls_use`` at startup.
- ``XTK_BATCH_ERR_UNKNOWN_CONTROL`` / ``STALE_HANDLE`` — An ``XtkCtrl`` handle
  belongs to a subtree that was already dropped in a prior batch.

Atomic Page Switching Pattern
-----------------------------

To switch pages in a multi-view imperative app (such as responding to
``NavigationView`` or ``TabView`` selection), drop the old page root and build
the new page subtree inside **one** ``XtkTxn``:

.. code-block:: c

   static bool switch_page(App *app, int next_page) {
       XtkTxn txn;
       if (!xtk_txn_begin(&app->scene, &txn)) return false;

       // 1. Drop the previous page subtree in the same transaction
       if (app->page_root != XTK_CTRL_INVALID) {
           xtk_txn_drop(&txn, xtk_ref_existing(app->page_root));
       }

       // 2. Build the new page under the persistent NavigationView handle
       XtkLocalId scroll = xtk_scroll_create(
           &txn, xtk_ref_existing(app->nav_ctrl),
           &(XtkScrollProps) {.set = XTK_SCROLL_GROW_MASK, .grow = 1.0f}
       );
       build_page_contents(app, &txn, xtk_ref_local(scroll), next_page);

       // 3. Commit both the drop and the new build atomically—zero flicker
       XtkBatchResult *res = xtk_txn_commit(&txn, NULL);
       if (!res) return false;

       // 4. Now that old subscriptions are detached, free old page callback contexts
       free_previous_page_contexts(app);
       app->page_root = resolve_ctrl(res, scroll);
       xtk_batchresult_destroy(res);
       return true;
   }

Freeing any heap-allocated ``userdata`` structures associated with the old page
*after* the drop transaction commits guarantees no dangling pointers while the
old controls were still live.
