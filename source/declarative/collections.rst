4. Virtualized Lists, Grids, Trees, & Caching
=============================================

Xent virtualizes collection controls out of the box: whether your dataset holds
50 items or 100,000 items, the host only instantiates controls for the visible
viewport window and recycles slots smoothly as the user scrolls.

Virtualized ``ListView``, ``ListBox``, & ``GridView``
-----------------------------------------------------

``xtk_list`` (``&flux_ctrl_list``), ``xtk_listbox``, ``xtk_gridview``, and
``xtk_repeater`` share ``XtkListDesc``. You supply ``.nitem`` and an
``item(ui, env, index)`` builder callback, and the host builds rows for the
visible viewport on demand:

.. code-block:: c

   static XtkEl *build_contact_row(XtkUi *ui, void *env, int index) {
       Model const *m = env;
       return xtk_row(
           ui, (XtkStackDesc) {.gap = 12, .align = XENT_FLEX_ALIGN_CENTER},
           xtk_kids(
               xtk_sized(xtk_text(ui, xtk_fmt(ui, "#%d", index), (XtkTextDesc) {.size = 12}), 64.0f, NAN),
               xtk_text(ui, xtk_fmt(ui, "Record %d (filter: %d)", index, m->active_filter), (XtkTextDesc) {0})
           )
       );
   }

   // Inside view():
   xtk_grow(
       xtk_list(ui, (XtkListDesc) {
           .nitem                = 100000,
           .itemh                = 40.0f,
           .item                 = build_contact_row,
           .env                  = (void *) m,
           .sel_mode             = XTK_LIST_SELECT_SINGLE,
           .sel                  = m->selected_row,
           .select               = xtk_msg(MSG_ROW_SELECT),
           .item_invoked_enabled = true,
           .invoke               = xtk_msg(MSG_ROW_ACTIVATE),
       }),
       1.0f
   )

Fixed vs. Variable-Height Rows
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- **Uniform fixed height**: Set ``.itemh = 40.0f`` (or your desired pixel row
  height) for ``O(1)`` exact scroll-thumb math.
- **Measured variable height (0.3.3 default)**: Leave ``.itemh = 0`` when rows
  contain multi-line wrapped notes or varying content. Fluxent measures realized
  rows dynamically and estimates off-screen extent from a rolling average.

Selection Modes & Rubber-Band Marquee Selection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Configure ``.sel_mode`` with:

- ``XTK_LIST_SELECT_SINGLE`` — Single row selection tracked via ``.sel`` and
  ``msg.i``.
- ``XTK_LIST_SELECT_NONE`` — Display-only or click-to-invoke list.
- ``XTK_LIST_SELECT_MULTIPLE`` — Clicking toggles checkboxes on individual rows.
- ``XTK_LIST_SELECT_EXTENDED`` — Desktop explorer selection supporting
  ``Ctrl+Click``, ``Shift+Click`` ranges, and ``Ctrl+A``. Set
  ``.rect_select = true`` in **0.3.3** to enable pointer drag rubber-band
  (marquee) box selection.

Grid Layouts & ``ItemsView``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For multi-column tile grids, use ``xtk_gridview`` with ``.itemw`` and ``.itemh``
(plus optional ``.ncol``; leave ``.ncol = 0`` to flow columns automatically to
the available width), or ``xtk_itemsview`` (``&flux_ctrl_itemsview``) with
``XTK_ITEMS_LAYOUT_UNIFORM_GRID`` / ``XTK_ITEMS_LAYOUT_FLOW``.

Grouped Lists with Sticky Headers (0.3.3)
-----------------------------------------

Both ``xtk_list`` and ``xtk_gridview`` support sectioned data with WinUI-style
inline sticky group headers. Pass an ``int32_t`` array of per-group item counts
in ``.groups``, the group count in ``.ngroup``, and a ``.group_header`` builder:

.. code-block:: c

   static int32_t const kSectionCounts[3] = { 4, 12, 7 }; // Total .nitem = 23

   static XtkEl *build_section_header(XtkUi *ui, void *env, int group) {
       (void) env;
       static char const *const kTitles[3] = { "Pinned", "Recent", "Archived" };
       return xtk_text(ui, kTitles[group], (XtkTextDesc) {.size = 18, .weight = XTK_FONT_SEMI_BOLD});
   }

   xtk_list(ui, (XtkListDesc) {
       .nitem        = 23,
       .itemh        = 40.0f,
       .groups       = kSectionCounts,
       .ngroup       = 3,
       .group_header = build_section_header,
       .item         = build_contact_row,
       .env          = (void *) m,
       .sel_mode     = XTK_LIST_SELECT_SINGLE,
       .sel          = m->selected_row,
       .select       = xtk_msg(MSG_ROW_SELECT),
   })

Notice that ``item(ui, env, index)`` still receives the logical item index
``0 .. nitem - 1``, while ``group_header`` receives ``0 .. ngroup - 1``. If you
need to map a flat realized row slot (headers and items interleaved) back to
``{group, item}``, call ``xtk_list_row(groups, ngroup, flat_row)``.

Details Table View with ``ColumnHeader`` (0.3.3)
------------------------------------------------

Attach ``xtk_colheader`` (register ``&flux_ctrl_colheader`` and
``&flux_ctrl_colitem``) to ``XtkListDesc.header`` to build a file-explorer
details table supporting click-to-sort arrows, drag column resizing,
double-click divider auto-fit, and drag column reordering:

.. code-block:: c

   XtkEl *hdr = xtk_colheader(ui, xtk_kids(
       xtk_colitem(ui, "Name", (XtkColItemDesc) {
           .width   = m->col_w[0],
           .min_width = 120.0f,
           .sort    = m->sort_col == 0 ? (m->sort_desc ? XTK_SORT_DESCENDING : XTK_SORT_ASCENDING) : XTK_SORT_NONE,
           .click   = xtk_msg_i(MSG_COL_SORT, 0),
           .resize  = xtk_msg_i(MSG_COL_RESIZE, 0),
           .fit     = xtk_msg_i(MSG_COL_FIT, 0),
           .reorder = xtk_msg_i(MSG_COL_REORDER, 0),
       }),
       xtk_colitem(ui, "Size", (XtkColItemDesc) {
           .width   = m->col_w[1],
           .align   = XTK_ALIGN_RIGHT,
           .click   = xtk_msg_i(MSG_COL_SORT, 1),
           .resize  = xtk_msg_i(MSG_COL_RESIZE, 1),
       })
   ));

   // Pass .header = hdr on XtkListDesc, and size cells in each row to m->col_w[c].

In ``update()``, ``.resize`` writes the new column width to ``msg.f`` (with your
column index in ``msg.i``), and ``.reorder`` provides the target slot in
``msg.i`` and source column in ``(int) msg.d``.

Hierarchical ``TreeView``
-------------------------

``xtk_tree`` (``&flux_ctrl_tree``) flattens visible nodes from a hierarchy of
``XtkTreeNodeDesc`` structs into a virtualized list with expand/collapse
chevrons:

.. code-block:: c

   static XtkTreeNodeDesc const kSrcFiles[] = {
       {.text = "main.c", .icon = "Document"},
       {.text = "view.c", .icon = "Document"},
   };

   XtkTreeNodeDesc roots[] = {
       {
           .text        = "src",
           .icon        = "Folder",
           .expanded    = m->src_expanded,
           .children    = kSrcFiles,
           .child_count = 2,
       },
       {.text = "xmake.lua", .icon = "Document"},
   };

   xtk_sized(
       xtk_tree(ui, (XtkTreeDesc) {
           .roots    = roots,
           .nroot    = 2,
           .sel_mode = XTK_TREE_SELECT_SINGLE,
           .sel      = m->tree_sel,
           .select   = xtk_msg(MSG_TREE_SELECT),
           .expand   = xtk_msg(MSG_TREE_EXPAND),
           .invoke   = xtk_msg(MSG_TREE_INVOKE),
       }),
       NAN, 280.0f
   )

``.select``, ``.expand``, and ``.invoke`` report the **flat visible row index**
in ``msg.i``; ``.expand`` also reports the new expanded boolean in ``msg.b``.

Reconciler Keys & Memoized Regions
----------------------------------

Preserving Identity with ``xtk_keyed_u64`` and ``xtk_keyed``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, sibling elements inside a container match by position. Whenever
children can reorder, insert/delete in the middle, or swap between distinct
pages inside one parent slot, assign stable keys so retained state (scroll
offset, focus, active animations, text cursor) follows the logical item:

- ``xtk_keyed_u64(el, item_id)`` — Zero-allocation 64-bit integer key (preferred
  for database IDs, enum page IDs, and tab IDs).
- ``xtk_keyed(ui, xtk_fmt(ui, "card-%s", slug), el)`` — String key (handy for
  named routes and diagnostics).

Skipping Unchanged Subtrees with Static & Memo Regions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When a screen combines a frequently ticking status indicator with a complex
sidebar or form that rarely changes, skip rebuilding and diffing the unchanged
region altogether:

- ``xtk_static_region(ui, 0x1001u, build_footer, NULL)`` — Calls ``build_footer``
  on the first frame and reuses the retained subtree on every subsequent frame.
- ``xtk_memo_region(ui, 0x1002u, m->sidebar_rev, build_sidebar, (void *) m)`` —
  Rebuilds the subtree only when ``m->sidebar_rev`` changes; increment
  ``m->sidebar_rev`` inside ``update()`` solely in handlers that affect sidebar
  data.
