import type * as p from "@bokehjs/core/properties"
import {Column as BkColumn, ColumnView as BkColumnView} from "@bokehjs/models/layouts/column"
import {div, button} from "@bokehjs/core/dom"
import {ModelEvent, server_event} from "@bokehjs/core/bokeh_events"
import type {Attrs} from "@bokehjs/core/types"
import {UIElementView} from "@bokehjs/models/ui/ui_element"
import {isNumber} from "@bokehjs/core/util/types"
import {LayoutDOMView} from "@bokehjs/models/layouts/layout_dom"

type A11yDialogView = {
  on(event: string, listener: () => void): void
  show(): void
  hide(): void
}

type A11yDialog = (container: HTMLElement) => Promise<{view: A11yDialogView}>
declare const A11yDialog: A11yDialog

@server_event("modal-dialog-event")
export class ModalDialogEvent extends ModelEvent {
  open: boolean

  constructor(open: boolean) {
    super()
    this.open = open
  }

  protected override get event_values(): Attrs {
    return {open: this.open}
  }

  static override from_values(values: object) {
    const {open} = values as {open: boolean}
    return new ModalDialogEvent(open)
  }
}

export class ModalView extends BkColumnView {
  declare model: Modal

  modal: A11yDialogView
  close_button: HTMLButtonElement

  override connect_signals(): void {
    super.connect_signals()
    const {show_close_button} = this.model.properties
    this.on_change([show_close_button], this.update_close_button)
    this.model.on_event(ModalDialogEvent, (event) => {
      event.open ? this.modal.show() : this.modal.hide()
    })
  }

  override render(): void {
    UIElementView.prototype.render.call(this)
    this.class_list.add(...this.css_classes())
    this.create_modal()
  }

  override async update_children(): Promise<void> {
    await LayoutDOMView.prototype.update_children.call(this)
  }

  create_modal(): void {
    const dialog = div({
      id: "pnx_dialog",
      class: "dialog-container bk-root",
      "aria-hidden": "true",
      style: {display: "none"},
    } as any)

    const dialog_overlay = div({class: "dialog-overlay"})
    if (this.model.background_close) {
      dialog_overlay.setAttribute("data-a11y-dialog-hide", "")
    }

    const {height, width, min_height, min_width, max_height, max_width} = this.model
    const convert_fn = (size: any) => { return isNumber(size) ? `${size}px` : size }
    const content = div({
      id: "pnx_dialog_content",
      class: "dialog-content",
      role: "document",
      style: {
        height: convert_fn(height),
        width: convert_fn(width),
        min_height: convert_fn(min_height),
        min_width: convert_fn(min_width),
        max_height: convert_fn(max_height),
        max_width: convert_fn(max_width),
        overflow: "auto",
      },
    } as any)
    for (const child_view of this.child_views) {
      const target = child_view.rendering_target() ?? content
      child_view.render_to(target)
    }

    this.close_button = button({
      id: "pnx_dialog_close",
      "data-a11y-dialog-hide": "",
      class: "pnx-dialog-close",
      ariaLabel: "Close this dialog window",
    } as any)
    this.close_button.innerHTML = "&#x2715"

    dialog.append(dialog_overlay)
    dialog.append(content)
    content.append(this.close_button)
    this.shadow_el.append(dialog)
    let first_open = false

    this.modal = new (window as any).A11yDialog(dialog)
    this.update_close_button()
    this.modal.on("show", () => {
      this.model.open = true
      dialog.style.display = ""
      if (!first_open) {
        requestAnimationFrame(() => { this.invalidate_layout() })
        first_open = true
      }
    })
    this.modal.on("hide", () => {
      this.model.open = false
      dialog.style.display = "none"
    })

    if (this.model.open) { this.modal.show() }
  }

  update_close_button(): void {
    if (this.model.show_close_button) {
      this.close_button.style.display = "block"
    } else {
      this.close_button.style.display = "none"
    }
  }
}

export namespace Modal {
  export type Attrs = p.AttrsOf<Props>

  export type Props = BkColumn.Props & {
    open: p.Property<boolean>
    show_close_button: p.Property<boolean>
    background_close: p.Property<boolean>
  }
}

export interface Modal extends Modal.Attrs {}

export class Modal extends BkColumn {
  declare properties: Modal.Props

  constructor(attrs?: Partial<Modal.Attrs>) {
    super(attrs)
  }

  static override __module__ = "panel.models.modal"
  static {
    this.prototype.default_view = ModalView
    this.define<Modal.Props>(({Bool}) => ({
      open: [Bool, false],
      show_close_button: [Bool, true],
      background_close: [Bool, true],
    }))
  }
}
