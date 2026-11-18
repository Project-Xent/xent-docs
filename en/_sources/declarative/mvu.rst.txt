1. The Elm MVU Loop & App Anatomy
=================================

Every declarative Xent program follows the **Model–View–Update (MVU)**
architecture introduced by Elm. Understanding how data, messages, and arena
memory flow through one frame makes every control in ``<xtk/xtk.h>``
predictable.

The Unidirectional Frame Loop
-----------------------------

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

1. **Model**: A plain C ``struct`` that stores your entire application state in
   one place—current page index, form text, selection indices, dialog flags, and
   loaded data.
2. **View** (``XtkEl *view(XtkUi *ui, void *model)``): A pure description
   function that reads ``Model`` and returns a lightweight tree of ``XtkEl *``
   descriptors allocated in ``ui``'s per-frame arena. Interactive controls carry
   ``XtkMsg`` values describing *what happened* when triggered.
3. **Update** (``void update(void *model, XtkMsg msg)``): When the user clicks a
   button, edits text, or scrolls a list, the host enqueues the control's
   ``XtkMsg``. Before the next frame builds, the runtime drains all queued
   messages through ``update()``, which inspects ``msg.tag`` and mutates
   ``Model`` in place.
4. **Reconcile & Commit**: Once the message queue drains, ``flux_run`` resets
   the ``XtkUi`` scratch arena, calls ``view()`` once, diffs the new element
   tree against the previous composition, and commits the minimal ``XtkBatch``
   mutations to the live Windows controls.

Dissecting the ``fluxent.decl`` Counter
---------------------------------------

Scaffolding a project with ``xmake create -l c -t fluxent.decl hello`` generates
this complete application in ``src/main.c``:

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

Designing ``Model`` and ``XtkMsg``
----------------------------------

Numbering Message Tags and Carrying Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``XtkMsg`` is a plain value struct defined in ``<xtk/xtk_msg.h>``:

.. code-block:: c

   typedef struct XtkMsg {
       int32_t tag;
       int32_t i;
       float   f;
       double  d;
       bool    b;
       void   *ptr;
   } XtkMsg;

- **Start your enum at** ``1``: Zero-initialized descriptor fields (such as an
  omitted ``.click`` in ``(XtkButtonDesc) {.style = XTK_BUTTON_SUBTLE}``) have
  ``tag == 0``, which tells the runtime to leave that event unbound.
- **Attach item indices with** ``xtk_msg_i``: When several buttons share one
  action (such as toolbar commands or dynamically generated rows), bind
  ``xtk_msg_i(MSG_REMOVE_ITEM, row_index)`` so ``update()`` receives both
  ``msg.tag`` and ``msg.i``.

Scaling ``update()`` with a Dispatch Table
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once an application grows past a dozen messages, split handlers into focused
functions indexed by a dispatch array (the pattern used by Fluxent's Gallery and
Installer Wizard):

.. code-block:: c

   typedef void (*MsgHandlerFn)(Model *m, XtkMsg msg);

   static void on_inc(Model *m, XtkMsg msg)   { (void) msg; m->n++; }
   static void on_dec(Model *m, XtkMsg msg)   { (void) msg; m->n--; }
   static void on_reset(Model *m, XtkMsg msg) { (void) msg; m->n = 0; }

   static MsgHandlerFn const kHandlers[] = {
       [MSG_INC]   = on_inc,
       [MSG_DEC]   = on_dec,
       [MSG_RESET] = on_reset,
   };

   static void update(void *model, XtkMsg msg) {
       size_t count = sizeof(kHandlers) / sizeof(kHandlers[0]);
       if (msg.tag > 0 && (size_t) msg.tag < count && kHandlers[msg.tag]) {
           kHandlers[msg.tag]((Model *) model, msg);
       }
   }

Computing Derived Values in ``view()``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Keep ``Model`` normalized—store raw state (such as ``file_done`` and
``file_count``) and compute formatted labels, percentages, and enabled/disabled
flags on the fly inside ``view()``. Because ``view()`` runs every time ``Model``
changes, derived UI properties stay consistent automatically.

Registering Control Modules
---------------------------

In **Fluxent 0.3.3**, controls link on demand through ``<fluxent/flux_controls.h>``:

- **Production builds**: Call ``flux_controls_use(&flux_ctrl_<name>)`` for each
  control module your views instantiate (for example ``&flux_ctrl_container``
  for ``xtk_column`` / ``xtk_row``, ``&flux_ctrl_text``, ``&flux_ctrl_button``).
  Unreferenced controls are stripped by the linker.
- **Prototyping**: Call ``flux_controls_all()`` once at startup to register the
  entire 70+ control catalog while iterating on UI layout.

Register modules before calling ``flux_run``.

Scratch Arena Memory Lifetimes
------------------------------

``XtkUi *`` owns a fast bump-pointer scratch arena that resets at the beginning
of every ``view()`` pass and stays alive until the frame's ``XtkBatch`` commits:

- **Dynamic text**: Allocate formatted strings with
  ``xtk_fmt(ui, "Count: %d", m->n)`` or copy transient buffers with
  ``xtk_strdup(ui, temp)``. String literals (``"Reset"``) and heap/static
  strings stored inside ``Model`` outlive the frame and can be passed directly.
- **Dynamic child arrays**: When building a variable number of children from a
  loop, allocate the child pointer array from the same arena and terminate it
  with ``XTK_END``:

  .. code-block:: c

     XtkEl **items = xtk_children_alloc(ui, count + 1);
     for (int i = 0; i < count; i++) {
         items[i] = xtk_text(ui, m->labels[i], (XtkTextDesc) {0});
     }
     items[count] = XTK_END;
     return xtk_column(ui, (XtkStackDesc) {.gap = 8}, items);
