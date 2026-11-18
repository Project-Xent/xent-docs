2. Layout, Typography, & Media
==============================

Declarative Xent layouts compose Flex containers, layout modifiers, scrollable
viewports, inherited typography, and asynchronous WIC images.

Flex Stacks, Cards, and ``xtk_kids``
------------------------------------

Four primary container builders arrange child elements:

- ``xtk_column(ui, desc, children)`` — Stacks children vertically (main axis:
  top to bottom; cross axis: horizontal).
- ``xtk_row(ui, desc, children)`` — Stacks children horizontally (main axis:
  left to right; cross axis: vertical).
- ``xtk_card(ui, desc, children)`` — Vertical Fluent card container with
  themed background fill, rounded corners, and stroke border.
- ``xtk_divider(ui)`` and ``xtk_spacer(ui)`` — Visual separator line and
  flexible empty space inside stacks.

Wrap inline child elements with ``xtk_kids(...)``, which builds a compound
literal array terminated by the ``XTK_END`` sentinel:

.. code-block:: c

   xtk_card(
       ui,
       (XtkStackDesc) {
           .gap     = 12,
           .padding = {20, 16, 20, 16},
           .align   = XENT_FLEX_ALIGN_STRETCH,
       },
       xtk_kids(
           xtk_text(ui, "Storage", (XtkTextDesc) {.size = 18, .weight = XTK_FONT_SEMI_BOLD}),
           xtk_divider(ui),
           xtk_row(
               ui, (XtkStackDesc) {.gap = 8, .align = XENT_FLEX_ALIGN_CENTER},
               xtk_kids(
                   xtk_text(ui, "System drive (C:)", (XtkTextDesc) {0}),
                   xtk_grow(xtk_spacer(ui), 1.0f),
                   xtk_text(ui, "142 GB free", (XtkTextDesc) {0})
               )
           )
       )
   )

``XtkStackDesc`` Reference
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 24 76

   * - Field
     - Behavior
   * - ``.gap``
     - Logical pixel spacing inserted between adjacent visible children.
   * - ``.padding``
     - ``XentInsets`` inner padding in ``{left, top, right, bottom}`` order.
   * - ``.align``
     - Cross-axis alignment: ``XENT_FLEX_ALIGN_START``, ``CENTER``, ``END``, or
       ``STRETCH``.
   * - ``.justify``
     - Main-axis distribution: ``XENT_FLEX_JUSTIFY_START``, ``CENTER``, ``END``,
       ``SPACE_BETWEEN``, ``SPACE_AROUND``, or ``SPACE_EVENLY``.
   * - ``.wrap``
     - ``XENT_FLEX_NO_WRAP`` (default) or ``XENT_FLEX_WRAP`` for multi-line
       flowing rows (such as tag chips or button toolbars).
   * - ``.fill``
     - Expands the stack to fill available space in its parent container.

Sizing and Layout Modifiers
---------------------------

Modifier functions wrap an ``XtkEl *`` and return the same element with layout
constraints attached:

- ``xtk_sized(el, width, height)`` — Constrains width, height, or both in
  logical pixels. Include ``<math.h>`` and pass ``NAN`` for any dimension that
  should measure from content (for example ``xtk_sized(btn, 120.0f, NAN)``).
- ``xtk_grow(el, factor)`` — Assigns Flex grow weight along the parent stack's
  main axis. Wrapping your root container or main content pane in
  ``xtk_grow(..., 1.0f)`` stretches it to fill the window.
- ``xtk_align(el, XENT_FLEX_ALIGN_...)`` — Overrides the parent stack's
  ``.align`` for one specific child (such as right-aligning a footer button in a
  left-aligned column via ``XENT_FLEX_ALIGN_END``).
- ``xtk_margin(el, (XentInsets) {left, top, right, bottom})`` — Adds outer
  spacing around an element.
- ``xtk_tooltip(ui, el, "Save Ctrl+S")`` — Attaches a themed tooltip shown on
  pointer hover and keyboard focus (register ``&flux_ctrl_tooltip``).

Scrollable Viewports & Controlled Scrolling
-------------------------------------------

Wrap tall content in ``xtk_scroll`` (register ``&flux_ctrl_scroll``) to gain
DirectManipulation touch/trackpad inertia and themed scrollbars:

.. code-block:: c

   xtk_grow(
       xtk_scroll(
           ui, (XtkScrollDesc) {0},
           xtk_kids(
               xtk_column(
                   ui, (XtkStackDesc) {.padding = {32, 24, 32, 24}, .gap = 16, .align = XENT_FLEX_ALIGN_STRETCH},
                   xtk_kids(/* page content */)
               )
           )
       ),
       1.0f
   )

Auto-Following Log Viewports
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``XtkScrollDesc`` also supports model-driven offsets for streaming logs or chat
panes:

- Pass ``NAN`` on an axis to leave scroll position under pure user control, a
  pixel offset to drive it from ``Model``, or ``INFINITY`` on ``.y`` to pin the
  viewport to the bottom as new lines arrive.
- Bind ``.scroll = xtk_msg(MSG_LOG_SCROLL)``: inside ``update()``, ``msg.f``
  reports the vertical offset and ``msg.b`` is ``true`` whenever the viewport is
  at the bottom, letting you pause auto-follow when the user scrolls up and
  resume automatically when they scroll back to the end:

  .. code-block:: c

     // In update():
     case MSG_LOG_SCROLL:
         m->log_follow = msg.b;
         m->log_y      = msg.f;
         break;

     // In view():
     xtk_scroll(
         ui,
         (XtkScrollDesc) {.x = NAN, .y = m->log_follow ? INFINITY : m->log_y, .scroll = xtk_msg(MSG_LOG_SCROLL)},
         xtk_kids(xtk_text(ui, m->log_buffer, (XtkTextDesc) {.size = 12, .selectable = true}))
     )

Typography & Inherited Text Styles
----------------------------------

``xtk_text(ui, content, desc)`` renders DirectWrite-shaped Unicode text:

- **Font inheritance (0.3.3)**: Leaving ``.size = 0`` or
  ``.weight = XTK_FONT_INHERIT`` inherits font size and weight from the nearest
  ancestor (defaulting to ``14.0f`` and ``XTK_FONT_REGULAR`` at the root). Set
  explicit values such as ``.size = 28, .weight = XTK_FONT_SEMI_BOLD`` for
  titles and section headers.
- **Wrapping, truncation, and ellipsis**: Text wraps to container width by
  default. Set ``.nowrap = true`` or ``.max_lines = 2`` together with
  ``.trim = XTK_TRIM_CHAR_ELLIPSIS``, ``XTK_TRIM_WORD_ELLIPSIS``, or
  ``XTK_TRIM_PATH_ELLIPSIS`` (ideal for long file paths).
- **Selectable labels**: Set ``.selectable = true`` on read-only output, error
  details, or log panes so users can drag-select text and copy it with
  ``Ctrl+C``.
- **Colors**: Pass an ``XtkColor`` in ``.color`` (leave zero-initialized to use
  the active Light/Dark theme's primary text brush automatically).

Images, SVG, Animated Media, & Nine-Grid
----------------------------------------

``xtk_image`` (register ``&flux_ctrl_image``) decodes raster images, animated
GIF, APNG, and vector SVG off the UI thread on the background thread pool:

.. code-block:: c

   XtkResource logo = flux_image_respath("assets/logo.svg");

   xtk_sized(
       xtk_image(ui, (XtkImageDesc) {
           .source  = logo,
           .stretch = XTK_IMAGE_UNIFORM,
           .opened  = xtk_msg(MSG_IMG_READY),
           .failed  = xtk_msg(MSG_IMG_ERROR),
       }),
       160.0f, 160.0f
   )

- ``flux_image_respath(path)`` interns the UTF-8 file path and returns a
  process-lifetime ``XtkResource`` handle.
- **Stretch modes**: ``XTK_IMAGE_UNIFORM`` (preserve aspect ratio inside
  bounds), ``XTK_IMAGE_FILL`` (stretch to both dimensions),
  ``XTK_IMAGE_UNIFORM_TO_FILL`` (fill bounds and clip overflow), or
  ``XTK_IMAGE_NONE``. Omitting ``xtk_sized`` lets the image measure to its
  natural pixel dimensions once its header decodes.
- **Nine-grid slicing**: Populate ``.nine = {left, top, right, bottom}`` with
  ``XTK_IMAGE_FILL`` to keep border corners unscaled while stretching edges and
  the center.
- **Avatars**: ``xtk_avatar`` (register ``&flux_ctrl_avatar``) renders a
  circular ``PersonPicture`` from ``.image``, ``.initials``, or
  ``.display_name`` with optional status badges.
