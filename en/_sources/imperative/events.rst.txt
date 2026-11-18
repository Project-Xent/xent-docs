4. Event Routing, Frame Sync, & Change Stamps
=============================================

Imperative Xent routes normalized UI events through capture, target, and bubble
phases and gives you full control over how state changes coalesce into visual
updates.

Three Ways to Subscribe to Events
---------------------------------

1. **Typed transaction helpers** (most common): Generated ``xtk_<ctrl>_on<event>``
   wrappers in ``<xtk/xtk_controls.h>`` subscribe on ``XTK_EVENT_PHASE_MASK_TARGET``
   while building a transaction:

   .. code-block:: c

      xtk_button_oninvoke(&txn, xtk_ref_local(btn), on_save_clicked, app);
      xtk_textbox_onchange(&txn, xtk_ref_local(box), on_name_edited, app);
      xtk_slider_onchange(&txn, xtk_ref_local(sld), on_volume_changed, app);

2. **Phase-aware transaction subscriptions**: ``xtk_txn_on`` lets you listen on
   any ``XtkEventId`` across ``XTK_EVENT_PHASE_MASK_CAPTURE`` (root down to
   parent), ``XTK_EVENT_PHASE_MASK_TARGET``, ``XTK_EVENT_PHASE_MASK_BUBBLE``
   (parent up to root), or ``XTK_EVENT_PHASE_MASK_ALL``:

   .. code-block:: c

      XtkSubRef sub = xtk_txn_on(
          &txn, xtk_ref_local(card),
          XTK_EVENT_INVOKE, XTK_EVENT_PHASE_MASK_BUBBLE,
          on_any_card_button, app
      );

   If you plan to unsubscribe dynamically later with ``xtk_txn_off(&txn, sub_id)``,
   map ``sub`` to its ``XtkSubId`` via ``result->subscriptions`` after commit.

3. **Direct host subscriptions**: ``flux_host_subscribe`` and
   ``flux_host_unsubscribe`` attach or remove listeners directly on a committed
   ``XtkCtrl`` outside a transaction.

.. important::

   The host borrows your ``void *arg`` (``userdata``) pointer until the
   subscription is removed (via ``xtk_txn_off``, ``flux_host_unsubscribe``, or
   dropping the target control's subtree) or ``flux_host_destroy`` runs. Keep
   ``arg`` alive in your ``App`` struct or a page-scoped arena until after the
   control is dropped.

Decoding ``XtkEvent`` and ``XtkEventPayload``
---------------------------------------------

Every ``XtkEventFn`` receives ``XtkEvent const *event``:

- ``event->source`` / ``event->target`` / ``event->current_target`` — Identify
  which ``XtkCtrl`` originated the event and which ancestor listener is
  currently running.
- ``event->cause`` — Distinguishes ``XTK_EVENT_CAUSE_USER``, ``PROGRAM``,
  ``BINDING``, and ``ACCESSIBILITY``.
- ``event->payload`` — Tagged union matched via ``event->payload.kind``:

.. list-table::
   :header-rows: 1
   :widths: 34 28 38

   * - ``event->payload.kind``
     - Union Member
     - Typical Events
   * - ``XTK_EVENT_PAYLOAD_NONE``
     - *(none)*
     - ``Button`` invoke, ``PullToRefresh`` trigger
   * - ``XTK_EVENT_PAYLOAD_BOOL``
     - ``u.b``
     - ``CheckBox`` / ``ToggleSwitch`` toggle, drag hover
   * - ``XTK_EVENT_PAYLOAD_I32``
     - ``u.i32``
     - ``ComboBox`` / ``ListView`` / ``TabView`` / ``NavigationView`` select,
       ``ContentDialog`` close result
   * - ``XTK_EVENT_PAYLOAD_F32``
     - ``u.f32``
     - ``Slider`` change, ``ColumnHeader`` resize
   * - ``XTK_EVENT_PAYLOAD_F64``
     - ``u.f64``
     - ``NumberBox`` / ``ScrollBar`` change
   * - ``XTK_EVENT_PAYLOAD_STRING``
     - ``u.string.{data, len}``
     - ``TextBox`` / ``PasswordBox`` edit, dropped files/text (**borrowed only
       during callback**—copy immediately!)
   * - ``XTK_EVENT_PAYLOAD_QUERY``
     - ``u.query.{text, len, index}``
     - ``AutoSuggestBox`` query/choose (**copy** ``text`` **during callback**)
   * - ``XTK_EVENT_PAYLOAD_INDEX_BOOL``
     - ``u.index_bool.{index, value}``
     - ``TreeView`` expand, ``CalendarView`` date toggle
   * - ``XTK_EVENT_PAYLOAD_RANGE``
     - ``u.range.{start, end}``
     - Range ``Slider`` change
   * - ``XTK_EVENT_PAYLOAD_WINDOW``
     - ``u.window.{first, last, lanes}``
     - ``XTK_EVENT_REALIZE`` on virtualized lists/grids
   * - ``XTK_EVENT_PAYLOAD_SCROLL``
     - ``u.scroll.{x, y, max_x, max_y}``
     - ``ScrollViewer`` viewport scroll

Return ``XTK_EVENT_HANDLED`` when your callback handles the event, combine
``XTK_EVENT_STOP_PROPAGATION`` or ``XTK_EVENT_STOP_IMMEDIATE`` to halt bubbling,
or return ``XTK_EVENT_CONTINUE`` (``0``) to let routing proceed.

Frame-Coalesced UI Synchronization
----------------------------------

Decoupling state updates from scene mutations with ``flux_app_onframe`` coalesces
multiple input events within a single vsync interval into one clean UI update:

.. code-block:: c

   // 1. Event callbacks update C state, copy any borrowed strings, and schedule a frame:
   static uint32_t on_name_change(void *arg, XtkEvent const *e) {
       App *app = arg;
       free(app->name);
       if (e->payload.kind == XTK_EVENT_PAYLOAD_STRING && e->payload.u.string.data) {
           uint32_t len = e->payload.u.string.len;
           app->name = malloc(len + 1);
           if (app->name) {
               memcpy(app->name, e->payload.u.string.data, len);
               app->name[len] = '\0';
           }
       } else {
           app->name = NULL;
       }
       app->dirty = true;
       flux_app_redraw(app->flux);
       return XTK_EVENT_HANDLED;
   }

   // 2. Once per frame before rendering, flush dirty state into retained controls:
   static void on_frame(void *arg) {
       App *app = arg;
       if (!app->dirty) return;
       app->dirty = false;

       char greeting[128];
       int len = snprintf(greeting, sizeof(greeting), "Hello, %s!",
                          app->name && app->name[0] ? app->name : "stranger");
       xtk_text_settext(&app->scene, app->greeting_label, greeting, (uint32_t) len, (XtkChangeStamp) {0});
   }

Controlled Inputs & ``XtkChangeStamp``
--------------------------------------

Every property write takes an ``XtkChangeStamp { XtkSourceId source; uint64_t revision; }``:

- **Programmatic writes to outputs or external resets**: Pass
  ``(XtkChangeStamp) {0}`` (where ``source == 0`` and ``revision == 0``). This
  authoritatively sets the control's property—use it when updating output
  labels, toggling buttons, or clearing a ``TextBox`` from a "Reset" button.
- **Controlled two-way echo**: When a user types into a ``TextBox``, the emitted
  ``XtkEvent`` carries a non-zero ``event->change`` stamp generated by the
  control. If your architecture echoes every model value back to the input
  control on ``on_frame``, forwarding that ``event->change`` stamp tells the
  host which edit revision your echo corresponds to—so newer keystrokes or active
  IME composition in flight on the control are preserved cleanly. In imperative
  code, updating the ``TextBox`` solely on external actions (such as a "Reset"
  button) keeps ``on_name_change`` even simpler because the control already
  displays the user's live edits.
