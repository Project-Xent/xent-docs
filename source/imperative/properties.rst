3. Typed Control Builders, Bitmasks, & Layouts
==============================================

``<xtk/xtk_controls.h>`` is generated directly from ``xent-kit/tools/catalog.lua``
and provides typed creation structs, property setters, and event subscription
helpers for all 70+ controls.

Naming Conventions in ``<xtk/xtk_controls.h>``
----------------------------------------------

Every catalog control ``<ctrl>`` (such as ``container``, ``card``, ``scroll``,
``text``, ``button``, ``checkbox``, ``slider``, ``textbox``, ``combo``,
``list``, ``nav``, ``dialog``, ``commandbar``) follows the same generated
pattern:

- **Properties struct**: ``Xtk<Ctrl>Props`` (for example ``XtkButtonProps``,
  ``XtkContainerProps``, ``XtkTextBoxProps``).
- **Bitmask constants**: ``XTK_<CTRL>_<PROP>_MASK`` (for example
  ``XTK_BUTTON_TEXT_MASK``, ``XTK_BUTTON_STYLE_MASK``, ``XTK_BUTTON_W_MASK``).
- **Transaction creator**:
  ``XtkLocalId xtk_<ctrl>_create(XtkTxn *txn, XtkNodeRef parent, Xtk<Ctrl>Props const *props);``
- **Live property setters**:
  ``bool xtk_<ctrl>_set<prop>(XtkScene *scene, XtkCtrl control, <type> value, XtkChangeStamp change);``
- **Event subscribers**:
  ``XtkSubRef xtk_<ctrl>_on<event>(XtkTxn *txn, XtkNodeRef target, XtkEventFn fn, void *arg);``

Shared layout fields—``w``, ``h``, ``grow``, ``shrink``, ``self``
(``XentFlexAlign``), ``ml``, ``mt``, ``mr``, ``mb`` (margins), and ``tip``
(tooltip string)—appear directly on every control's ``Xtk<Ctrl>Props`` struct.

Working with ``.set`` Masks and Strings
---------------------------------------

In C compound literals, omitted struct fields default to ``0``—which is also a
meaningful value for ``gap = 0.0f``, ``sel = 0``, or enum variant ``0``. The
``.set`` bitmask tells the encoder exactly which fields you populated:

.. code-block:: c

   XtkLocalId btn = xtk_button_create(
       &txn, parent,
       &(XtkButtonProps) {
           .set   = XTK_BUTTON_TEXT_MASK | XTK_BUTTON_ICON_MASK | XTK_BUTTON_STYLE_MASK,
           .text  = "Save",
           .icon  = "Save",
           .style = XTK_BUTTON_ACCENT,
       }
   );

String Length Rules
~~~~~~~~~~~~~~~~~~~

Every string property on ``Xtk<Ctrl>Props`` has both a pointer field (such as
``.text``, ``.icon``, ``.placeholder``, ``.tip``) and a byte-length field
(``.text_len``, ``.icon_len``, ``.placeholder_len``, ``.tip_len``), and string
setters take ``(char const *data, uint32_t len)``:

- **Null-terminated C strings**: Leaving ``.text_len = 0`` (or passing ``len = 0``
  to ``xtk_<ctrl>_set<prop>``) automatically measures ``strlen(data)`` when
  ``data`` is non-NULL.
- **Explicit byte slices & compile-time literals**: Passing a non-zero length
  skips ``strlen`` and supports non-null-terminated UTF-8 slices—for example
  ``#define LIT(s) .text = s, .text_len = sizeof(s) - 1`` for string literals or
  ``(uint32_t) snprintf(...)`` for formatted buffers.
- The batch copies string bytes immediately during ``xtk_*_create`` and
  ``xtk_*_set*``, so temporary stack buffers like ``char buf[64]`` are safe to
  reuse right after the call returns.

Writing Reusable Flex Layout Helpers
------------------------------------

Imperative code becomes as compact to read as declarative code once you wrap
your common column, row, card, and label patterns into small helper functions
(the exact technique used in ``fluxent/examples/gallery_imp/helpers.c``):

.. code-block:: c

   static XtkLocalId ui_column(XtkTxn *txn, XtkNodeRef parent, float gap, XentFlexAlign align) {
       return xtk_container_create(
           txn, parent,
           &(XtkContainerProps) {
               .set   = XTK_CONTAINER_DIR_MASK | XTK_CONTAINER_ITEMS_MASK
                      | XTK_CONTAINER_GAP_MASK | XTK_CONTAINER_SHRINK_MASK | XTK_CONTAINER_FITH_MASK,
               .dir   = XTK_STACK_COLUMN,
               .items = align,
               .gap   = gap,
               .fith  = true,
           }
       );
   }

   static XtkLocalId ui_row(XtkTxn *txn, XtkNodeRef parent, float gap, bool wrap) {
       return xtk_container_create(
           txn, parent,
           &(XtkContainerProps) {
               .set   = XTK_CONTAINER_DIR_MASK | XTK_CONTAINER_ITEMS_MASK
                      | XTK_CONTAINER_GAP_MASK | XTK_CONTAINER_WRAP_MASK,
               .dir   = XTK_STACK_ROW,
               .items = XENT_FLEX_ALIGN_CENTER,
               .gap   = gap,
               .wrap  = wrap ? XENT_FLEX_WRAP : XENT_FLEX_NO_WRAP,
           }
       );
   }

   static XtkLocalId ui_card(XtkTxn *txn, XtkNodeRef parent, float gap, float pad) {
       return xtk_card_create(
           txn, parent,
           &(XtkContainerProps) {
               .set   = XTK_CONTAINER_DIR_MASK | XTK_CONTAINER_ITEMS_MASK | XTK_CONTAINER_GAP_MASK
                      | XTK_CONTAINER_PL_MASK | XTK_CONTAINER_PT_MASK | XTK_CONTAINER_PR_MASK | XTK_CONTAINER_PB_MASK,
               .dir   = XTK_STACK_COLUMN,
               .items = XENT_FLEX_ALIGN_STRETCH,
               .gap   = gap,
               .pl    = pad, .pt = pad, .pr = pad, .pb = pad,
           }
       );
   }

Key ``XtkContainerProps`` layout flags:

- ``.dir``: ``XTK_STACK_COLUMN`` or ``XTK_STACK_ROW``.
- ``.items`` and ``.justify``: Cross-axis ``XentFlexAlign`` and main-axis
  ``XentFlexJustify``.
- ``.pl``, ``.pt``, ``.pr``, ``.pb``: Inner padding on left, top, right, bottom.
- ``.fill``: Stretches the container along its parent's main/cross space.
- ``.fith`` / ``.fitw``: Sizes the container tightly to its children's measured
  height or width inside scrollable regions.

Generic Property Access & Composite Setters
-------------------------------------------

Alongside the generated per-control wrappers, ``<xtk/xtk_scene.h>`` provides
control-agnostic helpers:

- **Setting properties inside a multi-op transaction**: Call
  ``xtk_txn_set(&txn, ref, XTK_PROP_WIDTH, (XtkValue) {.kind = XTK_VALUE_F32, .u.f32 = 240.0f}, (XtkChangeStamp) {0})``
  to batch multiple property updates across many controls into a single commit.
- **Reading current property values**: Call
  ``xtk_ctrl_get(&scene, ctrl, XTK_PROP_TEXT, &view, &stamp)``. String and byte
  slices inside ``XtkValueView`` point at the host's internal storage and stay
  valid until that property is modified again or the host is destroyed.
- **Populating composite item collections**: Controls that own structured child
  definitions have dedicated transaction helpers in ``<xtk/xtk_scene.h>``:

  - ``xtk_txn_setitems(&txn, target, strings, count)`` (and live
    ``xtk_ctrl_setitems``) — Populates ``ComboBox``, ``AutoSuggestBox``,
    ``BreadcrumbBar``, or ``LoopingSelector`` item lists.
  - ``xtk_txn_setselitems(&txn, target, selector_items, count)`` — Populates
    ``SelectorBar`` items with icons and labels.
  - ``xtk_txn_settabs(&txn, target, tab_descs, count)`` — Populates ``TabView``
    tab headers.
  - ``xtk_txn_settree(&txn, target, &tree_desc)`` — Populates a ``TreeView``
    hierarchy.
  - ``xtk_txn_setnav(&txn, target, &nav_desc)`` — Populates ``NavigationView``
    menu items, headers, separators, footer items, and integrated window title
    bar settings.
