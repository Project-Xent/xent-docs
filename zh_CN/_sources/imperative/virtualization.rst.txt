5. Imperative Virtualized Lists & Grouping
==========================================

In declarative mode, ``xtk_list`` accepts an ``item(ui, env, index)`` callback.
In imperative mode (and across language bindings), virtualization is driven by a
clean, control-neutral event contract: **the host tells you which visible
index window is on screen via** ``XTK_EVENT_REALIZE`` **, and you populate that
slice inside an** ``XtkTxn``.

How ``XTK_EVENT_REALIZE`` Works
-------------------------------

When you create a ``ListView``, ``ListBox``, ``GridView``, or ``ItemsRepeater``
with ``.nitem = 100000``, zero row controls exist initially. Whenever layout
measures the viewport or the user scrolls into a new row range, the host fires
``XTK_EVENT_REALIZE`` on the list control with
``event->payload.kind == XTK_EVENT_PAYLOAD_WINDOW``:

- ``event->payload.u.window.first`` — First visible row index to realize.
- ``event->payload.u.window.last`` — Last visible row index (inclusive) to
  realize.
- ``event->payload.u.window.lanes`` — Column count per row (``1`` for vertical
  lists, ``>= 1`` for multi-column ``GridView``).

Inside your ``XTK_EVENT_REALIZE`` callback, open one ``XtkTxn`` and perform four
steps:

1. **Drop** previously realized ``XtkCtrl`` items whose indices fell outside
   ``[first, last]``.
2. **Keep** items that remain inside the overlapping window so scrolling
   reuses existing controls in place.
3. **Create** ``XTK_CTRL_LISTITEM`` children for newly visible indices (inserting
   before the first kept item when scrolling upward, or appending at the end
   when scrolling downward) and populate their interior controls.
4. **Publish** ``XTK_PROP_REALIZED_FIRST = first`` on the list control and
   commit the transaction.

Complete 100,000-Row Imperative ``ListView`` Example
----------------------------------------------------

Remember to register ``&flux_ctrl_list``, ``&flux_ctrl_container``, and
``&flux_ctrl_text`` (or call ``flux_controls_all()``):

.. code-block:: c

   #define MAX_REALIZED_ROWS 128

   typedef struct VirtualList {
       XtkScene *scene;
       XtkCtrl   slots[MAX_REALIZED_ROWS];
       int       first;
       int       count;
   } VirtualList;

   static XtkCtrl find_ctrl(XtkBatchResult const *res, XtkLocalId local) {
       for (uint32_t i = 0; i < res->control_count; i++) {
           if (res->controls[i].local == local) return res->controls[i].control;
       }
       return XTK_CTRL_INVALID;
   }

   static void populate_row(XtkTxn *txn, XtkNodeRef item_slot, int index) {
       char label[64];
       int  len = snprintf(label, sizeof(label), "Row #%d", index);
       xtk_text_create(
           txn, item_slot,
           &(XtkTextProps) {
               .set      = XTK_TEXT_TEXT_MASK | XTK_TEXT_FONTSIZE_MASK,
               .text     = label,
               .text_len = (uint32_t) len,
               .fontsize = 14.0f,
           }
       );
   }

   static uint32_t on_list_realize(void *arg, XtkEvent const *event) {
       VirtualList *vl    = arg;
       int          first = event->payload.u.window.first;
       int          last  = event->payload.u.window.last;
       int          count = last >= first ? (last - first + 1) : 0;
       if (count > MAX_REALIZED_ROWS) count = MAX_REALIZED_ROWS;

       int keep_lo = first > vl->first ? first : vl->first;
       int old_end = vl->first + vl->count;
       int new_end = first + count;
       int keep_hi = old_end < new_end ? old_end : new_end;

       XtkTxn txn;
       if (!xtk_txn_begin(vl->scene, &txn)) return XTK_EVENT_HANDLED;

       XtkNodeRef list_ref = xtk_ref_existing(event->target);

       // 1. Drop rows that scrolled out of view
       for (int i = 0; i < vl->count; i++) {
           int idx = vl->first + i;
           if (idx < keep_lo || idx >= keep_hi) {
               xtk_txn_drop(&txn, xtk_ref_existing(vl->slots[i]));
           }
       }

       // 2. Keep overlapping rows and create newly visible XTK_CTRL_LISTITEM slots in order
       XtkNodeRef anchor = keep_hi > keep_lo
           ? xtk_ref_existing(vl->slots[keep_lo - vl->first])
           : xtk_ref_none();

       XtkNodeRef next_refs[MAX_REALIZED_ROWS];
       for (int i = 0; i < count; i++) {
           int idx = first + i;
           if (idx >= keep_lo && idx < keep_hi) {
               next_refs[i] = xtk_ref_existing(vl->slots[idx - vl->first]);
           } else {
               XtkNodeRef before = idx < keep_lo ? anchor : xtk_ref_none();
               XtkLocalId item   = xtk_txn_create(&txn, XTK_CTRL_LISTITEM, list_ref, before, NULL, 0);
               populate_row(&txn, xtk_ref_local(item), idx);
               next_refs[i] = xtk_ref_local(item);
           }
       }

       // 3. Publish the realized window origin and commit atomically
       xtk_txn_set(
           &txn, list_ref, XTK_PROP_REALIZED_FIRST,
           (XtkValue) {.kind = XTK_VALUE_I32, .u.i32 = first},
           (XtkChangeStamp) {0}
       );

       XtkBatchResult *res = xtk_txn_commit(&txn, NULL);
       if (!res) return XTK_EVENT_HANDLED;

       for (int i = 0; i < count; i++) {
           vl->slots[i] = next_refs[i].kind == XTK_REF_LOCAL
               ? find_ctrl(res, next_refs[i].u.local)
               : next_refs[i].u.existing;
       }
       vl->first = first;
       vl->count = count;
       xtk_batchresult_destroy(res);
       return XTK_EVENT_HANDLED;
   }

Attach ``on_list_realize`` when creating the list inside your initial build
transaction:

.. code-block:: c

   XtkLocalId list = xtk_list_create(
       &txn, parent,
       &(XtkListProps) {
           .set   = XTK_LIST_GROW_MASK | XTK_LIST_NITEM_MASK | XTK_LIST_ITEMH_MASK
                  | XTK_LIST_MODE_MASK | XTK_LIST_SEL_MASK,
           .grow  = 1.0f,
           .nitem = 100000,
           .itemh = 40.0f, // Set 0.0f in 0.3.3 for measured variable-height rows
           .mode  = XTK_LIST_SELECT_SINGLE,
           .sel   = -1,
       }
   );
   xtk_txn_on(&txn, xtk_ref_local(list), XTK_EVENT_REALIZE, XTK_EVENT_PHASE_MASK_TARGET, on_list_realize, &app->vlist);
   xtk_list_onselect(&txn, xtk_ref_local(list), on_row_selected, app);

Grouped Lists & Sticky Headers (0.3.3)
--------------------------------------

To group a ``ListView`` or ``GridView`` into sections with inline sticky headers:

1. Write the ``int32_t`` array of group sizes to ``XTK_PROP_GROUPS`` as an
   ``XTK_VALUE_BYTES`` slice during list creation:

   .. code-block:: c

      static int32_t const kGroupSizes[3] = { 5, 18, 9 };

      xtk_txn_set(
          &txn, xtk_ref_local(list), XTK_PROP_GROUPS,
          (XtkValue) {
              .kind    = XTK_VALUE_BYTES,
              .u.bytes = {(uint8_t const *) kGroupSizes, sizeof(kGroupSizes)},
          },
          (XtkChangeStamp) {0}
      );

2. In your ``XTK_EVENT_REALIZE`` handler, flat row indices interleave group
   headers and items. Call ``XtkListRow at = xtk_list_row(kGroupSizes, 3, row)``
   from ``<xtk/xtk.h>``:

   - When ``at.item < 0``, ``row`` is the header for ``at.group``—instantiate
     ``XTK_CTRL_GROUPHEADER`` via ``xtk_txn_create``.
   - When ``at.item >= 0``, ``row`` is logical item ``at.item`` inside
     ``at.group``—instantiate ``XTK_CTRL_LISTITEM``.
   - When ``window.first`` lands inside a group (``at.item >= 0``), also keep
     that group's header row realized right before ``first`` so the host can pin
     it as the sticky header at the top of the viewport. See
     ``groups_realize`` in ``fluxent/examples/gallery_imp/app.c`` for a drop-in
     reference implementation.
