import type { Device, LayoutEntry, LinkToolState } from '../../../types/topology.js'
import { createApp, h, type Component } from 'vue'
import { pinia } from '../../../stores/pinia.js'
import POPCockpit from '../../../components/cockpits/containers/POPCockpit.vue'
import CoreSiteCockpit from '../../../components/cockpits/containers/CoreSiteCockpit.vue'
import { makeDeviceClickHandler } from '../handlers.js'

export function drawContainers(options: {
  containersLayer: unknown
  devices: { devices: Device[] }
  linksStore: unknown
  selection: unknown
  linkTool: LinkToolState
  openDeviceContextMenu: (ev: MouseEvent, id: string) => void
  getPrepareDrag: () => ((ev: MouseEvent, id: string) => void) | undefined
  requestRedraw: () => void
  redrawSelection: () => void
  layoutCache: Record<string, LayoutEntry & { pinned?: boolean; type?: string }>
}) {
  const {
    containersLayer,
    devices,
    linksStore,
    selection,
    linkTool,
    openDeviceContextMenu,
    getPrepareDrag,
    requestRedraw,
    redrawSelection,
    layoutCache
  } = options

  const containerData = (devices.devices as Device[]).filter(
    (d) => d.type === 'POP' || d.type === 'CORE_SITE'
  )
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const containerGroups = (containersLayer as any)
    .selectAll('g.container-node')
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .data(containerData as any, (d: Device) => d.id)

  containerGroups
    .exit()
    .each(function (this: SVGGElement) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const app: any = (this as any).__cockpit_app__
      if (app && typeof app.unmount === 'function') {
        try {
          app.unmount()
        } catch {
          /* ignore */
        }
      }
    })
    .remove()

  const containerEnter = containerGroups
    .enter()
    .append('g')
    .attr('class', 'container-node')
    .style('pointer-events', 'all')
    .style('cursor', 'pointer')
    .each(function (this: SVGGElement, d: Device) {
      const mountId = `container-${d.id}`
      let mount = this.querySelector(`#${CSS.escape(mountId)}`)
      if (!mount) {
        mount = document.createElementNS('http://www.w3.org/2000/svg', 'g')
        mount.setAttribute('id', mountId)
        mount.setAttribute('class', 'container-root')
        this.appendChild(mount)
        const Comp = (d.type === 'POP' ? POPCockpit : CoreSiteCockpit) as Component
        // eslint-disable-next-line vue/one-component-per-file
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const app = createApp({ render: () => h(Comp as any, { deviceId: d.id }) })
        app.use(pinia)
        app.mount(mount)
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ;(this as any).__cockpit_app__ = app
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        ;(this as any).__cockpit_id__ = d.id
      }
    })

  containerEnter
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    .merge(containerGroups as any)
    .attr('transform', (d: Device) => `translate(${layoutCache[d.id].x},${layoutCache[d.id].y})`)
    .on(
      'click',
      makeDeviceClickHandler(
        linkTool,
        devices,
        linksStore,
        selection,
        requestRedraw,
        redrawSelection
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      ) as any
    )
    .on('contextmenu', (ev: MouseEvent, d: Device) => {
      openDeviceContextMenu(ev, d.id)
    })
    .on('mousedown', (ev: MouseEvent, d: Device) => {
      const fn = getPrepareDrag()
      if (fn) fn(ev, d.id)
    })
}
