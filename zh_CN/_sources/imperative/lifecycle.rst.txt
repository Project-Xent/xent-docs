1. App, Host, & Scene Lifecycle
===============================

An imperative Fluxent program wires together three objects—``FluxApp`` (window
and GPU pipeline), ``XtkHost`` (retained control store and batch validator), and
``XtkScene`` (the ergonomic handle passed to transactions and property setters).

Complete ``fluxent.imp`` Counter Walkthrough
--------------------------------------------

Running ``xmake create -l c -t fluxent.imp hello`` generates this complete
single-file application in ``src/main.c``:

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

   static uint32_t on_dec(void *arg, XtkEvent const *e) {
       (void) e;
       Counter *c = arg;
       return bump(c, c->n - 1);
   }

   static uint32_t on_reset(void *arg, XtkEvent const *e) {
       (void) e;
       return bump(arg, 0);
   }

   static void frame(void *arg) {
       Counter *c = arg;
       if (!c->dirty) return;
       c->dirty = false;
       char buf[32];
       int  len = snprintf(buf, sizeof(buf), "Value: %d", c->n);
       xtk_text_settext(&c->scene, c->value, buf, (uint32_t) len, (XtkChangeStamp) {});
   }

   static XtkLocalId button(XtkTxn *txn, XtkNodeRef row, XtkButtonProps props, XtkEventFn fn, Counter *c) {
       XtkLocalId id = xtk_button_create(txn, row, &props);
       xtk_button_oninvoke(txn, xtk_ref_local(id), fn, c);
       return id;
   }

   static bool build(Counter *c) {
       XtkTxn txn;
       if (!xtk_txn_begin(&c->scene, &txn)) return false;
       XtkNodeRef col = xtk_ref_local(xtk_container_create(
           &txn, xtk_ref_existing(xtk_scene_root(&c->scene)),
           &(XtkContainerProps) {
               .set = XTK_CONTAINER_DIR_MASK | XTK_CONTAINER_GROW_MASK | XTK_CONTAINER_ITEMS_MASK
                    | XTK_CONTAINER_GAP_MASK | XTK_CONTAINER_PL_MASK | XTK_CONTAINER_PT_MASK
                    | XTK_CONTAINER_PR_MASK | XTK_CONTAINER_PB_MASK,
               .dir   = XTK_STACK_COLUMN,
               .grow  = 1,
               .items = XENT_FLEX_ALIGN_START,
               .gap   = 16,
               .pl    = 32, .pt = 32, .pr = 32, .pb = 32,
           }
       ));
       xtk_text_create(
           &txn, col,
           &(XtkTextProps) {
               .set        = XTK_TEXT_TEXT_MASK | XTK_TEXT_FONTSIZE_MASK | XTK_TEXT_FONTWEIGHT_MASK,
               .fontsize   = 28,
               .fontweight = XTK_FONT_SEMI_BOLD,
               LIT("Counter"),
           }
       );
       XtkLocalId value = xtk_text_create(
           &txn, col,
           &(XtkTextProps) {.set = XTK_TEXT_TEXT_MASK | XTK_TEXT_FONTSIZE_MASK, .fontsize = 20, LIT("Value: 0")}
       );
       XtkNodeRef row = xtk_ref_local(xtk_container_create(
           &txn, col,
           &(XtkContainerProps) {
               .set   = XTK_CONTAINER_DIR_MASK | XTK_CONTAINER_ITEMS_MASK | XTK_CONTAINER_GAP_MASK,
               .dir   = XTK_STACK_ROW,
               .items = XENT_FLEX_ALIGN_CENTER,
               .gap   = 8,
           }
       ));
       button(&txn, row, (XtkButtonProps) {.set = XTK_BUTTON_TEXT_MASK | XTK_BUTTON_W_MASK, .w = 48, LIT("−")}, on_dec, c);
       button(&txn, row, (XtkButtonProps) {.set = XTK_BUTTON_TEXT_MASK | XTK_BUTTON_W_MASK | XTK_BUTTON_STYLE_MASK, .w = 48, .style = XTK_BUTTON_ACCENT, LIT("+")}, on_inc, c);
       button(&txn, row, (XtkButtonProps) {.set = XTK_BUTTON_TEXT_MASK | XTK_BUTTON_STYLE_MASK, .style = XTK_BUTTON_SUBTLE, LIT("Reset")}, on_reset, c);

       XtkBatchResult *result = xtk_txn_commit(&txn, NULL);
       if (!result) return false;
       for (uint32_t i = 0; i < result->control_count; i++) {
           if (result->controls[i].local == value) c->value = result->controls[i].control;
       }
       xtk_batchresult_destroy(result);
       return c->value != XTK_CTRL_INVALID;
   }

   int WINAPI WinMain(HINSTANCE hInst, HINSTANCE hPrev, LPSTR cmdLine, int showCmd) {
       (void) hInst; (void) hPrev; (void) cmdLine; (void) showCmd;

       flux_controls_use(&flux_ctrl_container);
       flux_controls_use(&flux_ctrl_text);
       flux_controls_use(&flux_ctrl_button);
       static Counter c = {.value = XTK_CTRL_INVALID};
       c.app = flux_app_create(
           &(FluxAppCfg) {.title = L"hello", .width = 480, .height = 320, .backdrop = FLUX_BACKDROP_MICA}
       );
       if (!c.app) return 1;
       XtkHost *host = flux_app_attachhost(c.app);
       int      rc   = 1;
       if (host) {
           c.scene = xtk_scene_fromhost(host);
           flux_app_onframe(c.app, frame, &c);
           if (build(&c)) rc = flux_app_run(c.app);
           flux_app_onframe(c.app, NULL, NULL);
           flux_host_destroy(host);
       }
       flux_app_destroy(c.app);
       return rc;
   }

Startup & Teardown Order
------------------------

Follow this exact five-step lifecycle in every imperative application:

1. **Register control modules**: Call ``flux_controls_use(&flux_ctrl_<name>)``
   for each control your transactions instantiate, or ``flux_controls_all()`` to
   register the entire catalog. Module names in ``<fluxent/flux_controls.h>``
   match the lowercase ``XTK_CTRL_<NAME>`` catalog suffix (for example
   ``flux_ctrl_container``, ``flux_ctrl_card``, ``flux_ctrl_scroll``,
   ``flux_ctrl_nav``, ``flux_ctrl_list``, ``flux_ctrl_dialog``).
2. **Create** ``FluxApp *``: ``flux_app_create(&cfg)`` creates the native Win32
   window, Direct2D/DirectWrite/DirectComposition renderer, theme tracker, IME
   bridge, and UI Automation provider. Initialize persistent ``XtkCtrl`` fields
   in your state struct to ``XTK_CTRL_INVALID``.
3. **Attach** ``XtkHost *`` **and wrap** ``XtkScene``:
   ``flux_app_attachhost(app)`` allocates a retained ``XtkHost`` bound to the
   window's layout root and rendering store. ``xtk_scene_fromhost(host)``
   returns a copyable ``XtkScene`` value struct whose root control handle is
   queried via ``xtk_scene_root(&scene)``.
4. **Commit initial UI and run the message loop**: Populate your initial scene
   inside an ``XtkTxn``, register an optional ``flux_app_onframe`` hook, and
   enter the blocking Win32 loop with ``flux_app_run(app)``.
5. **Tear down in reverse order**: After ``flux_app_run`` returns, detach the
   frame callback with ``flux_app_onframe(app, NULL, NULL)``, destroy the host
   with ``flux_host_destroy(host)``, destroy the app with
   ``flux_app_destroy(app)``, and free any application-owned heap allocations
   that were borrowed by event subscriptions.
