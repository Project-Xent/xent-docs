3. Forms, Pickers, & Controlled Inputs
======================================

In declarative Xent, form controls receive their current value from ``Model`` in
``view()`` and emit user changes back to ``update()`` via ``XtkMsg`` payloads.

``XtkMsg`` Payload Reference
----------------------------

Each interactive control populates specific fields of ``XtkMsg`` alongside your
message ``tag``:

.. list-table::
   :header-rows: 1
   :widths: 30 26 44

   * - Control Builder
     - Descriptor Field
     - Payload Field Read in ``update()``
   * - ``xtk_button`` / ``xtk_repeat`` / ``xtk_link``
     - ``.click``
     - ``msg.tag`` (and ``msg.i`` when bound via ``xtk_msg_i``)
   * - ``xtk_checkbox`` / ``xtk_switch`` / ``xtk_radio``
     - ``.change``
     - ``msg.b`` (``bool`` checked state)
   * - ``xtk_checkbox`` (three-state)
     - ``.change_state``
     - ``msg.i`` (``0`` unchecked, ``1`` checked, ``2`` indeterminate)
   * - ``xtk_slider``
     - ``.change`` / ``.change_range``
     - ``msg.f`` for single value; ``msg.f`` (start) and ``(float) msg.d`` (end)
       for range sliders
   * - ``xtk_number`` / ``xtk_rating`` / ``xtk_scroll_bar``
     - ``.change``
     - ``msg.d`` (``double`` value)
   * - ``xtk_combo`` / ``xtk_radiogroup`` / ``xtk_looping_selector``
     - ``.select``
     - ``msg.i`` (``int32_t`` selected index)
   * - ``xtk_textbox`` / ``xtk_password`` / ``xtk_combo`` (``.submit``)
     - ``.change`` / ``.submit``
     - ``(char const *) msg.ptr`` (borrowed UTF-8 string; duplicate with
       ``strdup`` inside ``update()``)
   * - ``xtk_suggest``
     - ``.on_text`` / ``.query`` / ``.on_chosen``
     - ``msg.ptr`` (UTF-8 text) for ``.on_text`` and ``.query``; ``msg.i``
       (suggestion index) for ``.on_chosen``
   * - ``xtk_date_picker`` / ``xtk_calendar_view``
     - ``.change`` / ``.select``
     - ``msg.i`` encoded as ``YYYYMMDD`` (see ``xtk_date``); calendar also sets
       ``msg.b`` (selected vs. deselected)
   * - ``xtk_time_picker``
     - ``.change``
     - ``msg.i`` (minutes from midnight, ``0``–``1439``)
   * - ``xtk_color_picker``
     - ``.change``
     - ``(uint32_t) msg.i`` packed ARGB color

Buttons, Links, and Menu Variants
---------------------------------

- **Standard & styled buttons** (``&flux_ctrl_button``): ``xtk_button`` supports
  ``XTK_BUTTON_STANDARD`` (``0``), ``XTK_BUTTON_ACCENT``, ``XTK_BUTTON_SUBTLE``,
  and ``XTK_BUTTON_TEXT``, plus named Fluent icons in ``.icon`` (such as
  ``"Save"``, ``"Share"``, ``"Delete"``, ``"Settings"``; pass ``NULL`` as the
  label for an icon-only button).
- **Repeat button & Hyperlink**: ``xtk_repeat`` (``&flux_ctrl_repeat``) fires
  ``.click`` repeatedly while held down; ``xtk_link`` (``&flux_ctrl_link``)
  opens ``.url`` or posts ``.click``.
- **Dropdown, Split, & ToggleSplit buttons** (``&flux_ctrl_dropdown``,
  ``&flux_ctrl_split``, ``&flux_ctrl_togglesplit``): Attach a popup menu array
  of ``XtkMenuItemDesc`` items:

  .. code-block:: c

     static XtkMenuItemDesc const kExportItems[] = {
         {.label = "Export PNG", .icon = "Save",  .click = {.tag = MSG_EXPORT, .i = 0}},
         {.label = "Export SVG", .icon = "Share", .click = {.tag = MSG_EXPORT, .i = 1}},
     };

     xtk_split(ui, "Export", (XtkSplitDesc) {
         .icon  = "Save",
         .click = xtk_msg_i(MSG_EXPORT, 0),
         .items = kExportItems,
         .nitem = 2,
     })

Toggles, Radio Groups, and Numeric Controls
-------------------------------------------

.. code-block:: c

   static XtkRadioItem const kThemes[] = {
       {.label = "Use system setting"},
       {.label = "Light"},
       {.label = "Dark"},
   };

   xtk_column(ui, (XtkStackDesc) {.gap = 14}, xtk_kids(
       xtk_checkbox(ui, "Launch at sign-in", (XtkToggleDesc) {
           .checked = m->autostart,
           .change  = xtk_msg(MSG_AUTOSTART),
       }),
       xtk_switch(ui, (XtkToggleDesc) {
           .checked = m->notifications,
           .change  = xtk_msg(MSG_NOTIFY),
       }),
       xtk_radiogroup(ui, (XtkRadioButtonsDesc) {
           .header      = "App theme",
           .items       = kThemes,
           .nitem       = 3,
           .sel         = m->theme_idx,
           .max_columns = 1,
           .select      = xtk_msg(MSG_THEME),
       }),
       xtk_sized(xtk_number(ui, (XtkNumberDesc) {
           .min    = 1.0,
           .max    = 64.0,
           .step   = 1.0,
           .value  = m->worker_threads,
           .change = xtk_msg(MSG_THREADS),
       }), 180.0f, NAN),
       xtk_sized(xtk_slider(ui, (XtkSliderDesc) {
           .min    = 0.0f,
           .max    = 100.0f,
           .step   = 5.0f,
           .value  = m->volume,
           .change = xtk_msg(MSG_VOLUME),
       }), 240.0f, NAN)
   ))

Remember to register each corresponding module (``&flux_ctrl_checkbox``,
``&flux_ctrl_switch``, ``&flux_ctrl_radiogroup``, ``&flux_ctrl_number``,
``&flux_ctrl_slider``) or call ``flux_controls_all()``.

Controlled Text Editing & ``AutoSuggestBox``
--------------------------------------------

``xtk_textbox`` (``&flux_ctrl_textbox``) and ``xtk_password``
(``&flux_ctrl_password``) support full DirectWrite grapheme navigation, undo/redo,
clipboard shortcuts, and CJK IME composition.

Because ``msg.ptr`` is borrowed only until ``update()`` returns, copy the UTF-8
string into heap or fixed buffer storage owned by ``Model``:

.. code-block:: c

   static void replace_str(char **slot, char const *next) {
       free(*slot);
       *slot = next ? strdup(next) : NULL;
   }

   // In update():
   case MSG_SEARCH_TEXT:
       replace_str(&m->query, (char const *) msg.ptr);
       rebuild_suggestions(m);
       break;
   case MSG_SEARCH_CHOSEN:
       if (msg.i >= 0 && msg.i < m->suggestion_count) {
           replace_str(&m->query, m->suggestions[msg.i]);
       }
       break;

   // In view() (register &flux_ctrl_suggest):
   xtk_sized(
       xtk_suggest(ui, "Search commands…", (XtkAutoSuggestDesc) {
           .content     = m->query,
           .suggestions = (char const *const *) m->suggestions,
           .nitem       = m->suggestion_count,
           .query_icon  = "Find",
           .on_text     = xtk_msg(MSG_SEARCH_TEXT),
           .query       = xtk_msg(MSG_SEARCH_SUBMIT),
           .on_chosen   = xtk_msg(MSG_SEARCH_CHOSEN),
       }),
       320.0f, NAN
   )

The Fluxent host tracks per-source ``XtkChangeStamp`` revisions automatically:
passing ``m->query`` back through ``.content`` updates the control cleanly on
external resets while preserving active IME composition and cursor selection
during live typing.

For multi-line editors or read-only text views, set ``.multiline = true`` and/or
``.readonly = true`` on ``XtkTextBoxDesc``.

ComboBox, Date, Time, Calendar, & Color Pickers
-----------------------------------------------

- **ComboBox** (``xtk_combo``, ``&flux_ctrl_combo``): Pass ``char const *const *``
  strings in ``.items``, ``.nitem``, and ``.sel``. Set ``.editable = true`` with
  ``.submit = xtk_msg(MSG_CUSTOM_VALUE)`` to allow free-form text entry in
  addition to preset choices.
- **Date & Calendar** (``xtk_date_picker`` / ``xtk_calendar_view``): Dates are
  encoded as ``int32_t`` values via ``xtk_date(year, month, day)``
  (``year * 10000 + month * 100 + day``, such as ``20261118``). Decode in
  ``update()`` with ``year = d / 10000``, ``month = (d / 100) % 100``,
  ``day = d % 100``.
- **TimePicker** (``xtk_time_picker``): ``.minutes`` stores minutes since
  ``00:00`` (``hours * 60 + mins``), with ``.has_time = true`` and
  ``.clock = XTK_CLOCK_24H`` or ``XTK_CLOCK_12H``.
- **ColorPicker** (``xtk_color_picker``): Takes an ``XtkColor`` in ``.color``,
  optional ``.alpha = true`` channel slider, and ``.spectrum`` layout, posting
  packed 32-bit ARGB integers to ``msg.i``.
