Declarative UI Guide
====================

This guide covers building applications on the **declarative track**
(``fluxent.decl``) using ``flux_run`` and the element builders in
``<xtk/xtk.h>``.

First Step: Understand the Elm MVU Architecture
-----------------------------------------------

Declarative Xent organizes every application around the **Model–View–Update
(MVU)** unidirectional loop (from the Elm Architecture):

.. code-block:: text

        ┌──────────────────────────────────────────┐
        │                                          ▼
   ┌─────────┐    view(ui, model)    ┌──────────────────────────┐
   │  Model  │ ────────────────────► │  Transient Element Tree  │
   └─────────┘                       └──────────────────────────┘
        ▲                                          │
        │ update(model, msg)                       │ User clicks / edits
        │                                          ▼
   ┌─────────┐                             ┌──────────────┐
   │ XtkMsg  │ ◄────────────────────────── │ Retained UI  │
   └─────────┘                             └──────────────┘

1. **Model**: A plain C ``struct`` holding your application state in one place
   (for example ``int n;`` for a counter).
2. **View** (``view(ui, model)``): A pure description function that reads the
   current ``Model`` and returns an ``XtkEl *`` tree describing the window
   contents. Interactive controls emit integer-tagged message values (such as
   ``xtk_msg(MSG_INC)``) when triggered.
3. **Update** (``update(model, msg)``): The single function where application
   state changes. When the user interacts with a control, the host posts its
   ``XtkMsg``, and ``update`` switches on ``msg.tag`` to update the ``Model``
   struct in place.
4. **Reconcile & Commit**: After draining pending messages for the frame,
   ``flux_run`` calls ``view`` again, diffs the new ``XtkEl *`` tree against the
   live retained controls, and commits the minimal changes in one atomic
   ``XtkBatch``.

Anatomy of the ``fluxent.decl`` Template
----------------------------------------

Running ``xmake create -l c -t fluxent.decl hello`` generates a complete MVU
counter in ``src/main.c``:

.. code-block:: c

   #include <fluxent/fluxent.h>
   #include <fluxent/flux_app.h>

   #include <math.h>

   enum {
       MSG_INC = 1,
       MSG_DEC,
       MSG_RESET,
   };

   typedef struct Model {
       int n;
   } Model;

   static void update(void *model, XtkMsg msg) {
       Model *m = model;
       switch (msg.tag) {
       case MSG_INC   : m->n++; break;
       case MSG_DEC   : m->n--; break;
       case MSG_RESET : m->n = 0; break;
       default        : break;
       }
   }

   static XtkEl *view(XtkUi *ui, void *model) {
       Model const *m = model;
       return xtk_column(
           ui, (XtkStackDesc) {.gap = 16, .padding = {32, 32, 32, 32}, .align = XENT_FLEX_ALIGN_START},
           xtk_kids(
               xtk_text(ui, "Counter", (XtkTextDesc) {.size = 28, .weight = XTK_FONT_SEMI_BOLD}),
               xtk_text(ui, xtk_fmt(ui, "Value: %d", m->n), (XtkTextDesc) {.size = 20}),
               xtk_row(
                   ui, (XtkStackDesc) {.gap = 8, .align = XENT_FLEX_ALIGN_CENTER},
                   xtk_kids(
                       xtk_sized(xtk_button(ui, "−", (XtkButtonDesc) {.click = xtk_msg(MSG_DEC)}), 48, NAN),
                       xtk_sized(
                           xtk_button(ui, "+", (XtkButtonDesc) {.style = XTK_BUTTON_ACCENT, .click = xtk_msg(MSG_INC)}),
                           48, NAN
                       ),
                       xtk_button(ui, "Reset", (XtkButtonDesc) {.style = XTK_BUTTON_SUBTLE, .click = xtk_msg(MSG_RESET)})
                   )
               )
           )
       );
   }

   int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmdLine, int showCmd) {
       (void) hInst; (void) hPrev; (void) cmdLine; (void) showCmd;

       flux_controls_use(&flux_ctrl_container);
       flux_controls_use(&flux_ctrl_text);
       flux_controls_use(&flux_ctrl_button);
       static Model model;
       return flux_run(
           &(FluxAppCfg) {.title = L"hello", .width = 480, .height = 320, .backdrop = FLUX_BACKDROP_MICA},
           &model, update, view
       );
   }

Key Details
~~~~~~~~~~~

1. **Message tags (** ``enum`` **)**: Start message enums at ``1`` so tag ``0``
   stays reserved for inert zero-initialized descriptors (``.click = {0}``).
   Use ``xtk_msg(MSG_INC)`` for a plain tag, or ``xtk_msg_i(tag, index)`` to
   attach an ``int32_t`` parameter in ``msg.i``.
2. **Control registration**: Register the control modules your app uses before
   calling ``flux_run``—selectively with ``flux_controls_use(&flux_ctrl_<name>)``
   for minimal binary size, or all at once with ``flux_controls_all()`` while
   prototyping.
3. **Window entry point**: GUI-subsystem builds enter via ``WinMain`` and configure
   the window title as a wide string ``L"..."`` on ``FluxAppCfg``.

Layout Containers, Children, and Modifiers
------------------------------------------

Container builders arrange children with ``xent-core``'s Flex layout engine:

- ``xtk_column(ui, desc, children)`` — Vertical stack (top to bottom).
- ``xtk_row(ui, desc, children)`` — Horizontal stack (left to right).
- ``xtk_card(ui, desc, children)`` — Styled Fluent card container.
- ``xtk_scroll(ui, scroll_desc, children)`` — Scrollable viewport.

Common ``XtkStackDesc`` fields:

- ``.gap`` — Spacing in logical pixels between adjacent children.
- ``.padding = {left, top, right, bottom}`` — Inner insets (``XentInsets``).
- ``.align`` — Cross-axis alignment (``XENT_FLEX_ALIGN_START``,
  ``XENT_FLEX_ALIGN_CENTER``, ``XENT_FLEX_ALIGN_STRETCH``).
- ``.justify`` — Main-axis distribution; ``.wrap = XENT_FLEX_WRAP`` enables
  multi-line wrapping.

Passing Children with ``xtk_kids``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Containers accept an ``XTK_END``-terminated array of ``XtkEl *`` pointers. Wrap
inline child lists with ``xtk_kids(...)``, which appends the ``XTK_END``
sentinel automatically:

.. code-block:: c

   xtk_row(ui, (XtkStackDesc) {.gap = 8}, xtk_kids(
       xtk_text(ui, "Left", (XtkTextDesc) {0}),
       xtk_spacer(ui),
       xtk_text(ui, "Right", (XtkTextDesc) {0})
   ))

When constructing a dynamic child list in a loop, allocate ``count + 1`` slots
with ``xtk_children_alloc(ui, count + 1)`` and set slot ``count`` to
``XTK_END``.

Layout Modifiers
~~~~~~~~~~~~~~~~

Wrap any ``XtkEl *`` with modifier functions to configure its layout behavior:

- ``xtk_sized(el, width, height)`` — Set explicit width and/or height; pass
  ``NAN`` (from ``<math.h>``) on an axis that sizes to content.
- ``xtk_grow(el, factor)`` — Expand along the parent stack's main axis (for
  example ``xtk_grow(el, 1.0f)`` to fill remaining space).
- ``xtk_align(el, XENT_FLEX_ALIGN_...)`` — Set cross-axis alignment for a single
  child.
- ``xtk_margin(el, (XentInsets) {left, top, right, bottom})`` — Add outer
  margins.
- ``xtk_tooltip(ui, el, "Hint")`` — Attach a hover and keyboard-focus tooltip.

Formatting Dynamic Strings
--------------------------

The reconciler reads strings from the element tree after ``view()`` returns, so
allocate dynamic per-frame text in ``XtkUi *``'s scratch arena:

- ``xtk_fmt(ui, "Value: %d", m->n)`` — Formats text with ``printf`` syntax into
  the frame arena and reclaims it automatically after commit.
- ``xtk_strdup(ui, str)`` — Copies a temporary string into the frame arena.

String literals and persistent buffers owned by ``Model`` that outlive the frame
can be passed directly to controls.

.. note::

   In **0.3.3**, ``xtk_text`` inherits font size and weight from its ancestors
   when ``.size`` is ``0`` or ``.weight`` is ``XTK_FONT_INHERIT`` (root default:
   14 px regular). Set ``.size`` and ``.weight`` explicitly on headings.

Common Controls and ``XtkMsg`` Payloads
---------------------------------------

When a user interacts with a control, the host populates the matching payload
field on ``XtkMsg`` alongside your tag:

.. list-table::
   :header-rows: 1
   :widths: 28 28 44

   * - Control Builder
     - Descriptor Event Field
     - Payload Field in ``update(model, msg)``
   * - ``xtk_button``
     - ``.click = xtk_msg(TAG)``
     - ``msg.tag`` (plus ``msg.i`` when built with ``xtk_msg_i``)
   * - ``xtk_checkbox`` / ``xtk_switch`` / ``xtk_radio``
     - ``.change = xtk_msg(TAG)``
     - ``msg.b`` (``bool`` checked state)
   * - ``xtk_slider``
     - ``.change = xtk_msg(TAG)``
     - ``msg.f`` (``float`` value)
   * - ``xtk_number`` / ``xtk_scroll_bar``
     - ``.change = xtk_msg(TAG)``
     - ``msg.d`` (``double`` value)
   * - ``xtk_combo`` / ``xtk_list`` / ``xtk_tabs`` / ``xtk_nav``
     - ``.select = xtk_msg(TAG)`` (or ``.change``)
     - ``msg.i`` (``int32_t`` selected index)
   * - ``xtk_textbox`` / ``xtk_password`` / ``xtk_suggest``
     - ``.change = xtk_msg(TAG)``
     - ``(char const *) msg.ptr`` (UTF-8 string borrowed for the ``update``
       call; copy with ``strdup`` into ``Model``)

Controlled Text Input
~~~~~~~~~~~~~~~~~~~~~

Duplicate the borrowed ``msg.ptr`` string inside ``update()`` to store edited
text in your ``Model``:

.. code-block:: c

   // Inside update():
   case MSG_NAME:
       free(m->name);
       m->name = msg.ptr ? strdup((char const *) msg.ptr) : NULL;
       break;

   // Inside view() (register &flux_ctrl_textbox or call flux_controls_all()):
   xtk_sized(
       xtk_textbox(ui, "Enter your name", (XtkTextBoxDesc) {
           .content = m->name,
           .change  = xtk_msg(MSG_NAME),
       }),
       280, NAN
   )

The host tracks ``XtkChangeStamp`` revisions automatically so binding
``m->name`` to ``.content`` preserves active IME composition and cursor
selection.

Virtualized Lists
-----------------

``xtk_list`` virtualizes large collections automatically, realizing rows for the
visible viewport on demand:

.. code-block:: c

   static XtkEl *build_row(XtkUi *ui, void *env, int index) {
       (void) env;
       return xtk_row(ui, (XtkStackDesc) {.gap = 12}, xtk_kids(
           xtk_sized(xtk_text(ui, xtk_fmt(ui, "#%d", index), (XtkTextDesc) {.size = 12}), 64, NAN),
           xtk_text(ui, xtk_fmt(ui, "Item %d", index), (XtkTextDesc) {0})
       ));
   }

   // Inside view() (register &flux_ctrl_list):
   xtk_grow(
       xtk_list(ui, (XtkListDesc) {
           .nitem    = 100000,
           .itemh    = 40,
           .item     = build_row,
           .sel_mode = XTK_LIST_SINGLE,
           .sel      = m->selected_row,
           .select   = xtk_msg(MSG_SELECT_ROW),
       }),
       1.0f
   )

.. tip::

   In **0.3.3**, ``.itemh = 0`` (the default) measures variable-height rows
   automatically; set a positive ``.itemh`` (such as ``40``) when all rows share
   a uniform height.

Keys and Memoized Regions
-------------------------

- **Sibling keys**: Wrap dynamically reordered or switched elements in
  ``xtk_keyed_u64(el, id)`` (allocation-free) or ``xtk_keyed(ui, key_str, el)``
  so the reconciler matches retained controls by explicit key across updates.
- **Memoized subtrees**: Wrap large unchanging subtrees in
  ``xtk_static_region(ui, region_id, build_fn, ctx)`` (built once) or
  ``xtk_memo_region(ui, region_id, revision, build_fn, ctx)`` (rebuilt when
  ``revision`` increments).

Exploring Every Control
-----------------------

Every declarative control in ``<xtk/xtk.h>`` has a runnable page in the
``fluxent`` repository under ``examples/gallery_decl/pages/``. Clone ``fluxent``
and run ``xmake run fluxent_gallery_decl`` to inspect them interactively.
